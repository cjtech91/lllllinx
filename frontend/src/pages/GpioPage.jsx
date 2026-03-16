import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, getErrorMessage } from "@/lib/api";

const physicalPins = Array.from({ length: 20 }, (_, idx) => ({
  left: idx * 2 + 1,
  right: idx * 2 + 2,
}));

export default function GpioPage() {
  const [status, setStatus] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [events, setEvents] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState("raspberry_pi");
  const [pins, setPins] = useState({ coin_pin: 2, relay_pin: 3, bill_pin: 4 });

  const loadData = async () => {
    const [statusRes, profilesRes, eventsRes] = await Promise.all([
      api.get("/system/status"),
      api.get("/hardware/profiles"),
      api.get("/gpio/events?limit=30"),
    ]);
    const state = statusRes.data.state;
    setStatus(statusRes.data);
    setProfiles(profilesRes.data.profiles || []);
    setEvents(eventsRes.data.events || []);
    setSelectedProfile(state.board_profile);
    setPins({
      coin_pin: state.coin_pin ?? 0,
      relay_pin: state.relay_pin ?? 0,
      bill_pin: state.bill_pin ?? 0,
    });
  };

  useEffect(() => {
    loadData();
  }, []);

  const pinHighlights = useMemo(
    () => new Set([Number(pins.coin_pin), Number(pins.relay_pin), Number(pins.bill_pin)]),
    [pins]
  );

  const applyProfile = async () => {
    try {
      await api.post("/hardware/profile", { profile_key: selectedProfile });
      toast.success("Hardware profile updated");
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Profile update failed"));
    }
  };

  const savePins = async (event) => {
    event.preventDefault();
    try {
      await api.put("/hardware/pins", {
        coin_pin: Number(pins.coin_pin),
        relay_pin: Number(pins.relay_pin),
        bill_pin: Number(pins.bill_pin),
      });
      toast.success("GPIO pin mapping saved");
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Cannot save pin mapping"));
    }
  };

  const setRelay = async (state) => {
    try {
      await api.post("/gpio/relay", { state });
      toast.success(`Relay turned ${state ? "ON" : "OFF"}`);
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Relay action failed"));
    }
  };

  const sendPulse = async (source) => {
    try {
      await api.post("/gpio/pulse", { source, pulses: 1, note: `${source} pulse from UI` });
      toast.success(`${source} pulse recorded`);
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Pulse logging failed"));
    }
  };

  return (
    <div className="space-y-6" data-testid="gpio-page">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card data-testid="hardware-profile-card">
          <CardHeader><CardTitle data-testid="hardware-profile-title">Board Profile</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <select
              data-testid="hardware-profile-select"
              className="w-full rounded-md border border-input bg-background h-9 px-3 text-sm"
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
            >
              {profiles.map((profile) => (
                <option
                  key={profile.key}
                  value={profile.key}
                  label={`${profile.label} ${profile.gpio_enabled ? "(GPIO enabled)" : "(GPIO disabled)"}`}
                />
              ))}
            </select>
            <Button data-testid="hardware-profile-apply-button" onClick={applyProfile} className="w-full">Apply profile</Button>
            <p className="text-xs text-muted-foreground" data-testid="gpio-enabled-state">
              GPIO enabled: <span className="mono-data">{String(status?.state?.gpio_enabled ?? false)}</span>
            </p>
          </CardContent>
        </Card>

        <Card data-testid="pin-mapping-card">
          <CardHeader><CardTitle data-testid="pin-mapping-title">Coin / Relay / Bill Pin Map</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={savePins} data-testid="pin-mapping-form">
              <Input data-testid="coin-pin-input" type="number" value={pins.coin_pin} onChange={(e) => setPins((p) => ({ ...p, coin_pin: e.target.value }))} required />
              <Input data-testid="relay-pin-input" type="number" value={pins.relay_pin} onChange={(e) => setPins((p) => ({ ...p, relay_pin: e.target.value }))} required />
              <Input data-testid="bill-pin-input" type="number" value={pins.bill_pin} onChange={(e) => setPins((p) => ({ ...p, bill_pin: e.target.value }))} required />
              <Button data-testid="pin-mapping-save-button" type="submit" className="w-full">Save mapping</Button>
            </form>
          </CardContent>
        </Card>

        <Card data-testid="relay-controls-card">
          <CardHeader><CardTitle data-testid="relay-controls-title">Relay & Pulse Controls</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm" data-testid="relay-live-state">Current relay: <span className="mono-data">{status?.state?.relay_state ? "ON" : "OFF"}</span></p>
            <div className="grid grid-cols-2 gap-2">
              <Button data-testid="relay-on-button" onClick={() => setRelay(true)}>Relay ON</Button>
              <Button data-testid="relay-off-button" variant="secondary" onClick={() => setRelay(false)}>Relay OFF</Button>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2">
              <Button data-testid="coin-pulse-button" variant="outline" onClick={() => sendPulse("coin")}>+ Coin Pulse</Button>
              <Button data-testid="bill-pulse-button" variant="outline" onClick={() => sendPulse("bill")}>+ Bill Pulse</Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card data-testid="gpio-pinout-card">
        <CardHeader><CardTitle data-testid="gpio-pinout-title">GPIO Pinout Grid (40-pin reference)</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-x-8 gap-y-1 w-fit font-mono text-xs" data-testid="gpio-pinout-grid">
            {physicalPins.map((pair) => (
              <div key={`pin-pair-${pair.left}`} className="contents">
                <div
                  className={`gpio-pin flex items-center gap-2 rounded px-2 py-1 ${pinHighlights.has(pair.left) ? "bg-primary/10 border border-primary/30" : ""}`}
                  data-testid={`gpio-pin-${pair.left}`}
                >
                  <span className="w-3 h-3 rounded-full border border-gray-400" />
                  <span>{pair.left}</span>
                </div>
                <div
                  className={`gpio-pin flex items-center gap-2 rounded px-2 py-1 ${pinHighlights.has(pair.right) ? "bg-primary/10 border border-primary/30" : ""}`}
                  data-testid={`gpio-pin-${pair.right}`}
                >
                  <span className="w-3 h-3 rounded-full border border-gray-400" />
                  <span>{pair.right}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground" data-testid="gpio-pinout-note">
            Highlight is visual for matching numbers. For OPI/NanoPi sysfs pins like 229/228/72, use configured values above.
          </p>
        </CardContent>
      </Card>

      <Card data-testid="gpio-events-card">
        <CardHeader><CardTitle data-testid="gpio-events-title">Pulse & Relay Event Log</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-auto rounded-md border" data-testid="gpio-events-table-wrapper">
            <table className="w-full text-sm" data-testid="gpio-events-table">
              <thead className="bg-muted/50 text-muted-foreground">
                <tr>
                  <th className="p-3 text-left">Type</th>
                  <th className="p-3 text-left">Pin</th>
                  <th className="p-3 text-left">Value</th>
                  <th className="p-3 text-left">Note</th>
                </tr>
              </thead>
              <tbody data-testid="gpio-events-table-body">
                {events.map((event) => (
                  <tr key={event.id} className="border-b" data-testid={`gpio-event-row-${event.id}`}>
                    <td className="p-3">{event.event_type}</td>
                    <td className="p-3 mono-data">{event.pin ?? "-"}</td>
                    <td className="p-3 mono-data">{event.value}</td>
                    <td className="p-3">{event.note}</td>
                  </tr>
                ))}
                {events.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-3 text-muted-foreground" data-testid="gpio-events-empty-state">No GPIO events yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
