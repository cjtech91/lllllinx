import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv


# Load external/public base URL from frontend env per test policy.
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(autouse=True, scope="session")
def validate_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not configured")


def test_health_and_root(api_client):
    # Module: platform health and root handshake
    root_res = api_client.get(f"{BASE_URL}/api/")
    assert root_res.status_code == 200
    root_data = root_res.json()
    assert root_data["message"] == "PisoFi Commander API online"

    health_res = api_client.get(f"{BASE_URL}/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "ok"
    assert "database" in health_data


def test_dashboard_summary_contract(api_client):
    # Module: dashboard summary metrics contract
    res = api_client.get(f"{BASE_URL}/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data.get("subvendo_count"), int)
    assert isinstance(data.get("sales_today"), (int, float))
    assert isinstance(data.get("relay_on"), bool)
    assert isinstance(data.get("vouchers"), dict)


def test_subvendo_crud_create_get_update_delete(api_client):
    # Module: sub-vendo VLAN CRUD and persistence
    suffix = str(uuid.uuid4())[:8]
    create_payload = {
        "name": f"TEST_vlan_{suffix}",
        "vlan_id": 3000 + int(time.time()) % 200,
        "subnet": "10.77.10.0",
        "gateway": "10.77.10.1",
        "dns": "1.1.1.1,8.8.8.8",
        "interface_name": f"v{suffix[:5]}",
        "parent_interface": "eth0",
        "rate_limit_kbps": 4096,
    }
    create_res = api_client.post(f"{BASE_URL}/api/subvendos", json=create_payload)
    assert create_res.status_code == 200
    created = create_res.json()["subvendo"]
    assert created["name"] == create_payload["name"]
    assert created["vlan_id"] == create_payload["vlan_id"]
    subvendo_id = created["id"]

    list_res = api_client.get(f"{BASE_URL}/api/subvendos")
    assert list_res.status_code == 200
    items = list_res.json()["subvendos"]
    fetched = next((x for x in items if x["id"] == subvendo_id), None)
    assert fetched is not None
    assert fetched["name"] == create_payload["name"]

    update_payload = {**create_payload, "name": f"TEST_vlan_upd_{suffix}", "rate_limit_kbps": 8192}
    upd_res = api_client.put(f"{BASE_URL}/api/subvendos/{subvendo_id}", json=update_payload)
    assert upd_res.status_code == 200
    updated = upd_res.json()["subvendo"]
    assert updated["name"] == update_payload["name"]
    assert updated["rate_limit_kbps"] == 8192

    list_res_2 = api_client.get(f"{BASE_URL}/api/subvendos")
    assert list_res_2.status_code == 200
    fetched_updated = next((x for x in list_res_2.json()["subvendos"] if x["id"] == subvendo_id), None)
    assert fetched_updated is not None
    assert fetched_updated["name"] == update_payload["name"]

    del_res = api_client.delete(f"{BASE_URL}/api/subvendos/{subvendo_id}")
    assert del_res.status_code == 200

    list_res_3 = api_client.get(f"{BASE_URL}/api/subvendos")
    assert list_res_3.status_code == 200
    deleted = next((x for x in list_res_3.json()["subvendos"] if x["id"] == subvendo_id), None)
    assert deleted is None


def test_voucher_profile_generate_and_redeem_flow(api_client):
    # Module: voucher profile, PIN generation, redemption lifecycle
    suffix = str(uuid.uuid4())[:8]
    profile_payload = {
        "name": f"TEST_profile_{suffix}",
        "minutes": 35,
        "price": 11.0,
    }
    profile_res = api_client.post(f"{BASE_URL}/api/voucher-profiles", json=profile_payload)
    assert profile_res.status_code == 200
    profile = profile_res.json()["profile"]
    assert profile["name"] == profile_payload["name"]
    profile_id = profile["id"]

    generate_res = api_client.post(
        f"{BASE_URL}/api/vouchers/generate",
        json={"profile_id": profile_id, "quantity": 1, "subvendo_id": None},
    )
    assert generate_res.status_code == 200
    generated = generate_res.json()["generated"]
    assert len(generated) == 1
    pin = generated[0]["pin"]
    assert generated[0]["status"] == "unused"

    list_res = api_client.get(f"{BASE_URL}/api/vouchers?status=unused&limit=200")
    assert list_res.status_code == 200
    row = next((x for x in list_res.json()["vouchers"] if x["pin"] == pin), None)
    assert row is not None
    assert row["status"] == "unused"

    redeem_res = api_client.post(f"{BASE_URL}/api/vouchers/redeem", json={"pin": pin})
    assert redeem_res.status_code == 200
    redeem_data = redeem_res.json()
    assert redeem_data["status"] == "active"
    assert redeem_data["access_minutes"] == profile_payload["minutes"]

    list_res_2 = api_client.get(f"{BASE_URL}/api/vouchers?status=active&limit=200")
    assert list_res_2.status_code == 200
    active_row = next((x for x in list_res_2.json()["vouchers"] if x["pin"] == pin), None)
    assert active_row is not None
    assert active_row["status"] == "active"

    double_redeem = api_client.post(f"{BASE_URL}/api/vouchers/redeem", json={"pin": pin})
    assert double_redeem.status_code == 400


def test_x86_gpio_disabled_behavior(api_client):
    # Module: hardware profile switching and x86 GPIO disabled guardrails
    set_x86 = api_client.post(f"{BASE_URL}/api/hardware/profile", json={"profile_key": "x86_x64"})
    assert set_x86.status_code == 200
    state = set_x86.json()["state"]
    assert state["board_profile"] == "x86_x64"
    assert state["gpio_enabled"] is False

    relay_res = api_client.post(f"{BASE_URL}/api/gpio/relay", json={"state": True})
    assert relay_res.status_code == 400
    assert "disabled" in relay_res.json()["detail"].lower()

    pulse_res = api_client.post(f"{BASE_URL}/api/gpio/pulse", json={"source": "coin", "pulses": 1, "note": "test"})
    assert pulse_res.status_code == 400
    assert "disabled" in pulse_res.json()["detail"].lower()

    pins_res = api_client.put(f"{BASE_URL}/api/hardware/pins", json={"coin_pin": 2, "relay_pin": 3, "bill_pin": 4})
    assert pins_res.status_code == 400

    # Restore GPIO-enabled profile to avoid cascading failures.
    restore = api_client.post(f"{BASE_URL}/api/hardware/profile", json={"profile_key": "raspberry_pi"})
    assert restore.status_code == 200
    assert restore.json()["state"]["gpio_enabled"] is True


def test_gpio_relay_pulse_and_events(api_client):
    # Module: relay and pulse endpoints plus event log propagation
    relay_on = api_client.post(f"{BASE_URL}/api/gpio/relay", json={"state": True})
    assert relay_on.status_code == 200
    assert relay_on.json()["relay_state"] is True

    pulse = api_client.post(
        f"{BASE_URL}/api/gpio/pulse",
        json={"source": "coin", "pulses": 2, "note": "TEST pulse from pytest"},
    )
    assert pulse.status_code == 200
    assert pulse.json()["source"] == "coin"
    assert pulse.json()["pulses"] == 2

    events_res = api_client.get(f"{BASE_URL}/api/gpio/events?limit=50")
    assert events_res.status_code == 200
    events = events_res.json()["events"]
    assert len(events) > 0
    assert any((e.get("event_type") == "coin" and e.get("value") == 2) for e in events)


def test_sales_report_and_config_export(api_client):
    # Module: sales report totals/trend and config export generation
    sales_res = api_client.get(f"{BASE_URL}/api/reports/sales")
    assert sales_res.status_code == 200
    sales = sales_res.json()
    assert isinstance(sales.get("totals"), dict)
    assert isinstance(sales["totals"].get("transactions"), int)
    assert isinstance(sales["totals"].get("revenue"), (int, float))
    assert isinstance(sales.get("trend"), list)

    cfg_res = api_client.get(f"{BASE_URL}/api/config/export")
    assert cfg_res.status_code == 200
    config = cfg_res.json()
    assert "script" in config
    assert config["script"].startswith("#!/usr/bin/env bash")
    assert "PisoFi Commander generated VLAN + QoS config" in config["script"]
