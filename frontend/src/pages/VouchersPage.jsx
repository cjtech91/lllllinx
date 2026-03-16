import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, getErrorMessage } from "@/lib/api";

export default function VouchersPage() {
  const [profiles, setProfiles] = useState([]);
  const [vouchers, setVouchers] = useState([]);
  const [subvendos, setSubvendos] = useState([]);
  const [profileForm, setProfileForm] = useState({ name: "", minutes: 60, price: 10 });
  const [generateForm, setGenerateForm] = useState({ profile_id: "", quantity: 10, subvendo_id: "" });
  const [redeemPin, setRedeemPin] = useState("");

  const loadData = async () => {
    const [profilesRes, vouchersRes, subvendosRes] = await Promise.all([
      api.get("/voucher-profiles"),
      api.get("/vouchers?limit=80"),
      api.get("/subvendos"),
    ]);
    setProfiles(profilesRes.data.profiles || []);
    setVouchers(vouchersRes.data.vouchers || []);
    setSubvendos(subvendosRes.data.subvendos || []);
    if (!generateForm.profile_id && profilesRes.data.profiles?.length > 0) {
      setGenerateForm((prev) => ({ ...prev, profile_id: String(profilesRes.data.profiles[0].id) }));
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const createProfile = async (event) => {
    event.preventDefault();
    try {
      await api.post("/voucher-profiles", {
        name: profileForm.name,
        minutes: Number(profileForm.minutes),
        price: Number(profileForm.price),
      });
      toast.success("Voucher profile created");
      setProfileForm({ name: "", minutes: 60, price: 10 });
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not create voucher profile"));
    }
  };

  const generatePins = async (event) => {
    event.preventDefault();
    try {
      await api.post("/vouchers/generate", {
        profile_id: Number(generateForm.profile_id),
        quantity: Number(generateForm.quantity),
        subvendo_id: generateForm.subvendo_id ? Number(generateForm.subvendo_id) : null,
      });
      toast.success("PIN vouchers generated");
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not generate PINs"));
    }
  };

  const redeemVoucher = async (event) => {
    event.preventDefault();
    try {
      const response = await api.post("/vouchers/redeem", { pin: redeemPin });
      toast.success(`PIN active until ${new Date(response.data.expires_at).toLocaleString()}`);
      setRedeemPin("");
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "PIN redemption failed"));
    }
  };

  return (
    <div className="space-y-6" data-testid="vouchers-page">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card data-testid="create-profile-card">
          <CardHeader><CardTitle data-testid="create-profile-title">Create PIN Profile</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={createProfile} data-testid="create-profile-form">
              <Input data-testid="profile-name-input" value={profileForm.name} onChange={(e) => setProfileForm((p) => ({ ...p, name: e.target.value }))} placeholder="Example: Happy Hour 90m" required />
              <Input data-testid="profile-minutes-input" type="number" value={profileForm.minutes} onChange={(e) => setProfileForm((p) => ({ ...p, minutes: e.target.value }))} min={1} required />
              <Input data-testid="profile-price-input" type="number" step="0.01" value={profileForm.price} onChange={(e) => setProfileForm((p) => ({ ...p, price: e.target.value }))} min={1} required />
              <Button data-testid="create-profile-submit-button" type="submit" className="w-full">Save profile</Button>
            </form>
          </CardContent>
        </Card>

        <Card data-testid="generate-pin-card">
          <CardHeader><CardTitle data-testid="generate-pin-title">Generate Time PINs</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={generatePins} data-testid="generate-pin-form">
              <select
                data-testid="generate-profile-select"
                className="w-full rounded-md border border-input bg-background h-9 px-3 text-sm"
                value={generateForm.profile_id}
                onChange={(e) => setGenerateForm((p) => ({ ...p, profile_id: e.target.value }))}
              >
                {profiles.map((profile) => (
                  <option
                    key={profile.id}
                    value={profile.id}
                    label={`${profile.name} (${profile.minutes}m / ₱${profile.price})`}
                  />
                ))}
              </select>
              <Input data-testid="generate-quantity-input" type="number" min={1} max={200} value={generateForm.quantity} onChange={(e) => setGenerateForm((p) => ({ ...p, quantity: e.target.value }))} required />
              <select
                data-testid="generate-subvendo-select"
                className="w-full rounded-md border border-input bg-background h-9 px-3 text-sm"
                value={generateForm.subvendo_id}
                onChange={(e) => setGenerateForm((p) => ({ ...p, subvendo_id: e.target.value }))}
              >
                <option value="">Unassigned sales bucket</option>
                {subvendos.map((sv) => (
                  <option
                    key={sv.id}
                    value={sv.id}
                    label={`${sv.name} (VLAN ${sv.vlan_id})`}
                  />
                ))}
              </select>
              <Button data-testid="generate-pin-submit-button" type="submit" className="w-full">Generate vouchers</Button>
            </form>
          </CardContent>
        </Card>

        <Card data-testid="redeem-pin-card">
          <CardHeader><CardTitle data-testid="redeem-pin-title">Redeem PIN</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={redeemVoucher} data-testid="redeem-pin-form">
              <Input data-testid="redeem-pin-input" value={redeemPin} onChange={(e) => setRedeemPin(e.target.value)} placeholder="Enter voucher PIN" required />
              <Button data-testid="redeem-pin-submit-button" type="submit" className="w-full">Redeem now</Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card data-testid="voucher-list-card">
        <CardHeader><CardTitle data-testid="voucher-list-title">Latest PIN Vouchers</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-auto rounded-md border" data-testid="voucher-table-wrapper">
            <table className="w-full text-sm" data-testid="voucher-table">
              <thead className="bg-muted/50 text-muted-foreground" data-testid="voucher-table-head">
                <tr>
                  <th className="p-3 text-left">PIN</th>
                  <th className="p-3 text-left">Profile</th>
                  <th className="p-3 text-left">Minutes</th>
                  <th className="p-3 text-left">Price</th>
                  <th className="p-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody data-testid="voucher-table-body">
                {vouchers.map((voucher) => (
                  <tr key={voucher.id} className="border-b" data-testid={`voucher-row-${voucher.id}`}>
                    <td className="p-3 mono-data" data-testid={`voucher-pin-${voucher.id}`}>{voucher.pin}</td>
                    <td className="p-3" data-testid={`voucher-profile-${voucher.id}`}>{voucher.profile_name}</td>
                    <td className="p-3 mono-data" data-testid={`voucher-minutes-${voucher.id}`}>{voucher.minutes}</td>
                    <td className="p-3 mono-data" data-testid={`voucher-price-${voucher.id}`}>₱{voucher.price}</td>
                    <td className="p-3" data-testid={`voucher-status-${voucher.id}`}>{voucher.status}</td>
                  </tr>
                ))}
                {vouchers.length === 0 && (
                  <tr>
                    <td className="p-3 text-muted-foreground" colSpan={5} data-testid="voucher-empty-state">No vouchers yet.</td>
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
