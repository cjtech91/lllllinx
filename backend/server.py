import json
import logging
import os
import random
import sqlite3
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# NOTE: MONGO_URL is intentionally preserved per protected environment rules.
_ = os.environ.get("MONGO_URL")

DB_PATH = ROOT_DIR / "pisofi.db"
DB_LOCK = Lock()

BOARD_PRESETS = {
    "orange_pi_h3_h5": {
        "label": "Orange Pi H3/H5 (One/PC/Zero old/3/4)",
        "gpio_enabled": True,
        "coin_pin": 12,
        "relay_pin": 11,
        "bill_pin": 6,
    },
    "orange_pi_zero_3": {
        "label": "Orange Pi Zero 3 (H616/H618)",
        "gpio_enabled": True,
        "coin_pin": 229,
        "relay_pin": 228,
        "bill_pin": 72,
    },
    "raspberry_pi": {
        "label": "Raspberry Pi (BCM)",
        "gpio_enabled": True,
        "coin_pin": 2,
        "relay_pin": 3,
        "bill_pin": 4,
    },
    "nanopi_h3_h5": {
        "label": "NanoPi H3/H5 Compatible",
        "gpio_enabled": True,
        "coin_pin": 12,
        "relay_pin": 11,
        "bill_pin": 6,
    },
    "x86_x64": {
        "label": "x86/x64 (EFI + Legacy)",
        "gpio_enabled": False,
        "coin_pin": None,
        "relay_pin": None,
        "bill_pin": None,
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with DB_LOCK:
        conn = get_conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS system_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                board_profile TEXT NOT NULL,
                gpio_enabled INTEGER NOT NULL,
                coin_pin INTEGER,
                relay_pin INTEGER,
                bill_pin INTEGER,
                relay_state INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS voucher_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                minutes INTEGER NOT NULL,
                price REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subvendos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                vlan_id INTEGER NOT NULL UNIQUE,
                subnet TEXT NOT NULL,
                gateway TEXT NOT NULL,
                dns TEXT NOT NULL,
                interface_name TEXT NOT NULL,
                parent_interface TEXT NOT NULL,
                rate_limit_kbps INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pin TEXT NOT NULL UNIQUE,
                profile_id INTEGER NOT NULL,
                minutes INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL,
                subvendo_id INTEGER,
                created_at TEXT NOT NULL,
                redeemed_at TEXT,
                expires_at TEXT,
                FOREIGN KEY (profile_id) REFERENCES voucher_profiles(id),
                FOREIGN KEY (subvendo_id) REFERENCES subvendos(id)
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                amount REAL NOT NULL,
                duration_minutes INTEGER NOT NULL,
                voucher_id INTEGER,
                subvendo_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (voucher_id) REFERENCES vouchers(id),
                FOREIGN KEY (subvendo_id) REFERENCES subvendos(id)
            );

            CREATE TABLE IF NOT EXISTS gpio_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                pin INTEGER,
                value INTEGER,
                note TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        state = conn.execute("SELECT id FROM system_state WHERE id = 1").fetchone()
        if not state:
            preset = BOARD_PRESETS["raspberry_pi"]
            conn.execute(
                """
                INSERT INTO system_state (id, board_profile, gpio_enabled, coin_pin, relay_pin, bill_pin, relay_state, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    "raspberry_pi",
                    int(preset["gpio_enabled"]),
                    preset["coin_pin"],
                    preset["relay_pin"],
                    preset["bill_pin"],
                    utc_now_iso(),
                ),
            )

        profile_count = conn.execute("SELECT COUNT(*) AS c FROM voucher_profiles").fetchone()["c"]
        if profile_count == 0:
            defaults = [
                ("Quick 30m", 30, 5.0, utc_now_iso()),
                ("Standard 1h", 60, 10.0, utc_now_iso()),
                ("Extended 3h", 180, 25.0, utc_now_iso()),
            ]
            conn.executemany(
                "INSERT INTO voucher_profiles (name, minutes, price, created_at) VALUES (?, ?, ?, ?)",
                defaults,
            )

        conn.commit()
        conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict:
    return dict(row) if row else {}


def read_system_state(conn: sqlite3.Connection) -> Dict:
    row = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()
    data = row_to_dict(row)
    data["gpio_enabled"] = bool(data.get("gpio_enabled", 0))
    data["relay_state"] = bool(data.get("relay_state", 0))
    return data


def read_cpu_temperature() -> Optional[float]:
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if not thermal_path.exists():
        return None
    try:
        raw = thermal_path.read_text().strip()
        return round(int(raw) / 1000, 1)
    except Exception:
        return None


def read_memory_usage_percent() -> Optional[float]:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            lines = f.readlines()
        mem_total = int(lines[0].split()[1])
        mem_available = int(lines[2].split()[1])
        used = mem_total - mem_available
        return round((used / mem_total) * 100, 1)
    except Exception:
        return None


def ensure_expired_vouchers(conn: sqlite3.Connection) -> None:
    now_iso = utc_now_iso()
    conn.execute(
        """
        UPDATE vouchers
        SET status = 'expired'
        WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at < ?
        """,
        (now_iso,),
    )


def unique_pin(conn: sqlite3.Connection, length: int = 8) -> str:
    digits = string.digits
    for _ in range(25):
        pin = "".join(random.choice(digits) for _ in range(length))
        exists = conn.execute("SELECT id FROM vouchers WHERE pin = ?", (pin,)).fetchone()
        if not exists:
            return pin
    raise HTTPException(status_code=500, detail="Unable to generate unique PIN")


class VoucherProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    minutes: int = Field(gt=0, le=1440)
    price: float = Field(gt=0)


class GenerateVoucherIn(BaseModel):
    profile_id: int
    quantity: int = Field(default=1, ge=1, le=200)
    subvendo_id: Optional[int] = None


class RedeemVoucherIn(BaseModel):
    pin: str = Field(min_length=4, max_length=12)


class SubvendoIn(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    vlan_id: int = Field(ge=2, le=4094)
    subnet: str = Field(min_length=7, max_length=32)
    gateway: str = Field(min_length=7, max_length=32)
    dns: str = Field(min_length=7, max_length=64)
    interface_name: str = Field(min_length=2, max_length=20)
    parent_interface: str = Field(min_length=2, max_length=20)
    rate_limit_kbps: int = Field(ge=128, le=1_000_000)


class HardwareProfileIn(BaseModel):
    profile_key: str


class PinConfigIn(BaseModel):
    coin_pin: int = Field(ge=0)
    relay_pin: int = Field(ge=0)
    bill_pin: int = Field(ge=0)


class RelayIn(BaseModel):
    state: bool


class PulseIn(BaseModel):
    source: Literal["coin", "bill"]
    pulses: int = Field(default=1, ge=1, le=50)
    note: Optional[str] = Field(default="")


app = FastAPI(title="PisoFi Commander API")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
def root() -> Dict[str, str]:
    return {"message": "PisoFi Commander API online"}


@api_router.get("/health")
def health() -> Dict:
    return {
        "status": "ok",
        "database": str(DB_PATH),
        "timestamp": utc_now_iso(),
    }


@api_router.get("/hardware/profiles")
def hardware_profiles() -> Dict:
    profiles = []
    for key, data in BOARD_PRESETS.items():
        profiles.append(
            {
                "key": key,
                "label": data["label"],
                "gpio_enabled": data["gpio_enabled"],
                "coin_pin": data["coin_pin"],
                "relay_pin": data["relay_pin"],
                "bill_pin": data["bill_pin"],
            }
        )
    return {"profiles": profiles}


@api_router.post("/hardware/profile")
def set_hardware_profile(payload: HardwareProfileIn) -> Dict:
    preset = BOARD_PRESETS.get(payload.profile_key)
    if not preset:
        raise HTTPException(status_code=404, detail="Unknown board profile")

    with DB_LOCK:
        conn = get_conn()
        conn.execute(
            """
            UPDATE system_state
            SET board_profile = ?, gpio_enabled = ?, coin_pin = ?, relay_pin = ?, bill_pin = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                payload.profile_key,
                int(preset["gpio_enabled"]),
                preset["coin_pin"],
                preset["relay_pin"],
                preset["bill_pin"],
                utc_now_iso(),
            ),
        )
        conn.commit()
        state = read_system_state(conn)
        conn.close()
        return {"message": "Hardware profile updated", "state": state}


@api_router.put("/hardware/pins")
def update_pin_config(payload: PinConfigIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        state = read_system_state(conn)
        if not state["gpio_enabled"]:
            conn.close()
            raise HTTPException(status_code=400, detail="GPIO is disabled for x86/x64 profile")

        conn.execute(
            """
            UPDATE system_state
            SET coin_pin = ?, relay_pin = ?, bill_pin = ?, updated_at = ?
            WHERE id = 1
            """,
            (payload.coin_pin, payload.relay_pin, payload.bill_pin, utc_now_iso()),
        )
        conn.commit()
        updated = read_system_state(conn)
        conn.close()
    return {"message": "Pin configuration updated", "state": updated}


@api_router.get("/system/status")
def system_status() -> Dict:
    conn = get_conn()
    state = read_system_state(conn)
    conn.close()

    one_minute_load = os.getloadavg()[0]
    return {
        "state": state,
        "board_label": BOARD_PRESETS[state["board_profile"]]["label"],
        "cpu_load_1m": round(one_minute_load, 2),
        "memory_usage_percent": read_memory_usage_percent(),
        "cpu_temp_c": read_cpu_temperature(),
        "timestamp": utc_now_iso(),
    }


@api_router.post("/gpio/relay")
def set_relay(payload: RelayIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        state = read_system_state(conn)
        if not state["gpio_enabled"]:
            conn.close()
            raise HTTPException(status_code=400, detail="GPIO relay control is disabled on x86/x64")

        relay_pin = state["relay_pin"]
        conn.execute(
            "UPDATE system_state SET relay_state = ?, updated_at = ? WHERE id = 1",
            (int(payload.state), utc_now_iso()),
        )
        conn.execute(
            "INSERT INTO gpio_events (event_type, pin, value, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                "relay",
                relay_pin,
                int(payload.state),
                "Relay toggled from API",
                utc_now_iso(),
            ),
        )
        conn.commit()
        updated = read_system_state(conn)
        conn.close()
    return {"message": "Relay state updated", "relay_state": updated["relay_state"]}


@api_router.post("/gpio/pulse")
def register_pulse(payload: PulseIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        state = read_system_state(conn)
        if not state["gpio_enabled"]:
            conn.close()
            raise HTTPException(status_code=400, detail="GPIO pulse input is disabled on x86/x64")

        target_pin = state["coin_pin"] if payload.source == "coin" else state["bill_pin"]
        conn.execute(
            "INSERT INTO gpio_events (event_type, pin, value, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                payload.source,
                target_pin,
                payload.pulses,
                payload.note or f"{payload.source} pulse received",
                utc_now_iso(),
            ),
        )
        conn.commit()
        conn.close()
    return {"message": "Pulse event recorded", "source": payload.source, "pulses": payload.pulses}


@api_router.get("/gpio/events")
def gpio_events(limit: int = Query(default=30, ge=1, le=200)) -> Dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, event_type, pin, value, note, created_at FROM gpio_events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return {"events": [row_to_dict(r) for r in rows]}


@api_router.get("/voucher-profiles")
def list_voucher_profiles() -> Dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, minutes, price, created_at FROM voucher_profiles ORDER BY minutes ASC"
    ).fetchall()
    conn.close()
    return {"profiles": [row_to_dict(r) for r in rows]}


@api_router.post("/voucher-profiles")
def create_voucher_profile(payload: VoucherProfileIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO voucher_profiles (name, minutes, price, created_at) VALUES (?, ?, ?, ?)",
                (payload.name.strip(), payload.minutes, payload.price, utc_now_iso()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, minutes, price, created_at FROM voucher_profiles WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            result = row_to_dict(row)
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=409, detail="Voucher profile name already exists")
        conn.close()
    return {"message": "Voucher profile created", "profile": result}


@api_router.get("/vouchers")
def list_vouchers(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        ensure_expired_vouchers(conn)
        conn.commit()
        if status:
            rows = conn.execute(
                """
                SELECT v.id, v.pin, v.profile_id, vp.name AS profile_name, v.minutes, v.price, v.status,
                       v.subvendo_id, sv.name AS subvendo_name, v.created_at, v.redeemed_at, v.expires_at
                FROM vouchers v
                JOIN voucher_profiles vp ON v.profile_id = vp.id
                LEFT JOIN subvendos sv ON sv.id = v.subvendo_id
                WHERE v.status = ?
                ORDER BY v.id DESC LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT v.id, v.pin, v.profile_id, vp.name AS profile_name, v.minutes, v.price, v.status,
                       v.subvendo_id, sv.name AS subvendo_name, v.created_at, v.redeemed_at, v.expires_at
                FROM vouchers v
                JOIN voucher_profiles vp ON v.profile_id = vp.id
                LEFT JOIN subvendos sv ON sv.id = v.subvendo_id
                ORDER BY v.id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        conn.close()
    return {"vouchers": [row_to_dict(r) for r in rows]}


@api_router.post("/vouchers/generate")
def generate_vouchers(payload: GenerateVoucherIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        profile = conn.execute(
            "SELECT id, name, minutes, price FROM voucher_profiles WHERE id = ?",
            (payload.profile_id,),
        ).fetchone()
        if not profile:
            conn.close()
            raise HTTPException(status_code=404, detail="Voucher profile not found")

        if payload.subvendo_id is not None:
            subvendo = conn.execute("SELECT id FROM subvendos WHERE id = ?", (payload.subvendo_id,)).fetchone()
            if not subvendo:
                conn.close()
                raise HTTPException(status_code=404, detail="Sub-vendo not found")

        created = []
        for _ in range(payload.quantity):
            pin = unique_pin(conn)
            cursor = conn.execute(
                """
                INSERT INTO vouchers (pin, profile_id, minutes, price, status, subvendo_id, created_at)
                VALUES (?, ?, ?, ?, 'unused', ?, ?)
                """,
                (
                    pin,
                    profile["id"],
                    profile["minutes"],
                    profile["price"],
                    payload.subvendo_id,
                    utc_now_iso(),
                ),
            )
            conn.execute(
                """
                INSERT INTO sales (source, amount, duration_minutes, voucher_id, subvendo_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "voucher_pin",
                    profile["price"],
                    profile["minutes"],
                    cursor.lastrowid,
                    payload.subvendo_id,
                    utc_now_iso(),
                ),
            )
            created.append(
                {
                    "pin": pin,
                    "minutes": profile["minutes"],
                    "price": profile["price"],
                    "status": "unused",
                }
            )
        conn.commit()
        conn.close()
    return {"message": "Voucher PINs generated", "generated": created}


@api_router.post("/vouchers/redeem")
def redeem_voucher(payload: RedeemVoucherIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        ensure_expired_vouchers(conn)
        voucher = conn.execute(
            "SELECT id, pin, minutes, status, redeemed_at, expires_at FROM vouchers WHERE pin = ?",
            (payload.pin.strip(),),
        ).fetchone()
        if not voucher:
            conn.close()
            raise HTTPException(status_code=404, detail="PIN not found")

        if voucher["status"] != "unused":
            conn.close()
            raise HTTPException(status_code=400, detail=f"PIN is {voucher['status']}")

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=voucher["minutes"])
        conn.execute(
            """
            UPDATE vouchers
            SET status = 'active', redeemed_at = ?, expires_at = ?
            WHERE id = ?
            """,
            (now.isoformat(), expires.isoformat(), voucher["id"]),
        )

        state = read_system_state(conn)
        conn.execute(
            "INSERT INTO gpio_events (event_type, pin, value, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                "relay",
                state.get("relay_pin"),
                1,
                f"Voucher {payload.pin.strip()} redeemed; relay trigger queued",
                utc_now_iso(),
            ),
        )

        conn.commit()
        conn.close()

    return {
        "message": "PIN redeemed",
        "pin": payload.pin.strip(),
        "status": "active",
        "access_minutes": voucher["minutes"],
        "expires_at": expires.isoformat(),
    }


@api_router.get("/subvendos")
def list_subvendos() -> Dict:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, name, vlan_id, subnet, gateway, dns, interface_name, parent_interface, rate_limit_kbps, created_at
        FROM subvendos ORDER BY vlan_id ASC
        """
    ).fetchall()
    conn.close()
    return {"subvendos": [row_to_dict(r) for r in rows]}


@api_router.post("/subvendos")
def create_subvendo(payload: SubvendoIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        try:
            cursor = conn.execute(
                """
                INSERT INTO subvendos (name, vlan_id, subnet, gateway, dns, interface_name, parent_interface, rate_limit_kbps, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.name.strip(),
                    payload.vlan_id,
                    payload.subnet.strip(),
                    payload.gateway.strip(),
                    payload.dns.strip(),
                    payload.interface_name.strip(),
                    payload.parent_interface.strip(),
                    payload.rate_limit_kbps,
                    utc_now_iso(),
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, vlan_id, subnet, gateway, dns, interface_name, parent_interface, rate_limit_kbps, created_at FROM subvendos WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            result = row_to_dict(row)
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=409, detail="Sub-vendo name or VLAN already exists")
        conn.close()

    return {"message": "Sub-vendo created", "subvendo": result}


@api_router.put("/subvendos/{subvendo_id}")
def update_subvendo(subvendo_id: int, payload: SubvendoIn) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        existing = conn.execute("SELECT id FROM subvendos WHERE id = ?", (subvendo_id,)).fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail="Sub-vendo not found")
        try:
            conn.execute(
                """
                UPDATE subvendos
                SET name = ?, vlan_id = ?, subnet = ?, gateway = ?, dns = ?, interface_name = ?, parent_interface = ?, rate_limit_kbps = ?
                WHERE id = ?
                """,
                (
                    payload.name.strip(),
                    payload.vlan_id,
                    payload.subnet.strip(),
                    payload.gateway.strip(),
                    payload.dns.strip(),
                    payload.interface_name.strip(),
                    payload.parent_interface.strip(),
                    payload.rate_limit_kbps,
                    subvendo_id,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, vlan_id, subnet, gateway, dns, interface_name, parent_interface, rate_limit_kbps, created_at FROM subvendos WHERE id = ?",
                (subvendo_id,),
            ).fetchone()
            result = row_to_dict(row)
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=409, detail="Sub-vendo name or VLAN already exists")
        conn.close()
    return {"message": "Sub-vendo updated", "subvendo": result}


@api_router.delete("/subvendos/{subvendo_id}")
def delete_subvendo(subvendo_id: int) -> Dict:
    with DB_LOCK:
        conn = get_conn()
        existing = conn.execute("SELECT id FROM subvendos WHERE id = ?", (subvendo_id,)).fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail="Sub-vendo not found")
        conn.execute("DELETE FROM subvendos WHERE id = ?", (subvendo_id,))
        conn.commit()
        conn.close()
    return {"message": "Sub-vendo deleted"}


@api_router.get("/reports/sales")
def sales_report() -> Dict:
    conn = get_conn()
    ensure_expired_vouchers(conn)
    conn.commit()

    totals = conn.execute(
        """
        SELECT
            COUNT(*) AS transactions,
            ROUND(COALESCE(SUM(amount), 0), 2) AS revenue,
            COALESCE(SUM(duration_minutes), 0) AS minutes
        FROM sales
        """
    ).fetchone()

    by_subvendo = conn.execute(
        """
        SELECT COALESCE(sv.name, 'Unassigned') AS name,
               ROUND(COALESCE(SUM(s.amount), 0), 2) AS revenue,
               COUNT(*) AS transactions,
               COALESCE(SUM(s.duration_minutes), 0) AS minutes
        FROM sales s
        LEFT JOIN subvendos sv ON sv.id = s.subvendo_id
        GROUP BY COALESCE(sv.name, 'Unassigned')
        ORDER BY revenue DESC
        """
    ).fetchall()

    trend = conn.execute(
        """
        SELECT SUBSTR(created_at, 1, 10) AS day,
               ROUND(COALESCE(SUM(amount), 0), 2) AS revenue
        FROM sales
        GROUP BY SUBSTR(created_at, 1, 10)
        ORDER BY day DESC
        LIMIT 7
        """
    ).fetchall()

    conn.close()
    return {
        "totals": row_to_dict(totals),
        "by_subvendo": [row_to_dict(r) for r in by_subvendo],
        "trend": [row_to_dict(r) for r in reversed(trend)],
    }


@api_router.get("/dashboard/summary")
def dashboard_summary() -> Dict:
    conn = get_conn()
    ensure_expired_vouchers(conn)
    conn.commit()

    voucher_counts = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'unused' THEN 1 ELSE 0 END) AS unused,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) AS expired
        FROM vouchers
        """
    ).fetchone()

    subvendos_count = conn.execute("SELECT COUNT(*) AS c FROM subvendos").fetchone()["c"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sales_today = conn.execute(
        "SELECT ROUND(COALESCE(SUM(amount), 0), 2) AS revenue FROM sales WHERE SUBSTR(created_at, 1, 10) = ?",
        (today,),
    ).fetchone()["revenue"]

    state = read_system_state(conn)
    top_subvendos = conn.execute(
        """
        SELECT COALESCE(sv.name, 'Unassigned') AS name, ROUND(SUM(s.amount), 2) AS revenue
        FROM sales s
        LEFT JOIN subvendos sv ON sv.id = s.subvendo_id
        GROUP BY COALESCE(sv.name, 'Unassigned')
        ORDER BY revenue DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()

    return {
        "vouchers": row_to_dict(voucher_counts),
        "subvendo_count": subvendos_count,
        "sales_today": sales_today,
        "relay_on": state["relay_state"],
        "board_profile": state["board_profile"],
        "top_subvendos": [row_to_dict(r) for r in top_subvendos],
        "cpu_load_1m": round(os.getloadavg()[0], 2),
    }


@api_router.get("/config/export")
def export_linux_config() -> Dict:
    conn = get_conn()
    state = read_system_state(conn)
    subvendos = conn.execute(
        """
        SELECT name, vlan_id, subnet, gateway, dns, interface_name, parent_interface, rate_limit_kbps
        FROM subvendos
        ORDER BY vlan_id ASC
        """
    ).fetchall()
    conn.close()

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# PisoFi Commander generated VLAN + QoS config",
        f"# Generated at: {utc_now_iso()}",
        f"# Board profile: {state['board_profile']} (GPIO enabled={str(state['gpio_enabled']).lower()})",
        f"# coin_pin={state.get('coin_pin')} relay_pin={state.get('relay_pin')} bill_pin={state.get('bill_pin')}",
        "",
    ]

    if not subvendos:
        lines.extend(
            [
                "# No sub-vendo VLAN entries yet.",
                "# Create sub-vendos from the web panel to generate network commands.",
            ]
        )
    else:
        for sv in subvendos:
            iface_vlan = f"{sv['parent_interface']}.{sv['vlan_id']}"
            lines.extend(
                [
                    f"# ---- {sv['name']} ----",
                    f"ip link add link {sv['parent_interface']} name {iface_vlan} type vlan id {sv['vlan_id']} || true",
                    f"ip addr add {sv['gateway']}/24 dev {iface_vlan} || true",
                    f"ip link set dev {iface_vlan} up",
                    f"tc qdisc replace dev {iface_vlan} root tbf rate {sv['rate_limit_kbps']}kbit burst 32kbit latency 400ms",
                    f"# DNS: {sv['dns']}",
                    f"# Client subnet: {sv['subnet']}",
                    "",
                ]
            )

    return {"script": "\n".join(lines), "generated_at": utc_now_iso()}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup() -> None:
    init_db()
    logger.info("PisoFi Commander backend started with SQLite at %s", DB_PATH)


@app.on_event("shutdown")
def shutdown() -> None:
    logger.info("PisoFi Commander backend shutting down")