import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, getErrorMessage } from "@/lib/api";

const defaultForm = {
  name: "",
  vlan_id: 20,
  subnet: "192.168.20.0",
  gateway: "192.168.20.1",
  dns: "1.1.1.1,8.8.8.8",
  interface_name: "vendo20",
  parent_interface: "eth0",
  rate_limit_kbps: 2048,
};

export default function VlansPage() {
  const [subvendos, setSubvendos] = useState([]);
  const [form, setForm] = useState(defaultForm);

  const loadSubvendos = async () => {
    const response = await api.get("/subvendos");
    setSubvendos(response.data.subvendos || []);
  };

  useEffect(() => {
    loadSubvendos();
  }, []);

  const createSubvendo = async (event) => {
    event.preventDefault();
    try {
      await api.post("/subvendos", {
        ...form,
        vlan_id: Number(form.vlan_id),
        rate_limit_kbps: Number(form.rate_limit_kbps),
      });
      toast.success("Sub-vendo VLAN created");
      setForm(defaultForm);
      await loadSubvendos();
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not create sub-vendo"));
    }
  };

  const removeSubvendo = async (id) => {
    try {
      await api.delete(`/subvendos/${id}`);
      toast.success("Sub-vendo deleted");
      await loadSubvendos();
    } catch (error) {
      toast.error(getErrorMessage(error, "Delete failed"));
    }
  };

  return (
    <div className="space-y-6" data-testid="vlans-page">
      <Card data-testid="create-subvendo-card">
        <CardHeader>
          <CardTitle data-testid="create-subvendo-title">Create Sub-Vendo VLAN</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3" onSubmit={createSubvendo} data-testid="create-subvendo-form">
            <Input data-testid="subvendo-name-input" placeholder="Name" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} required />
            <Input data-testid="subvendo-vlan-input" type="number" placeholder="VLAN ID" value={form.vlan_id} onChange={(e) => setForm((p) => ({ ...p, vlan_id: e.target.value }))} required />
            <Input data-testid="subvendo-subnet-input" placeholder="Subnet" value={form.subnet} onChange={(e) => setForm((p) => ({ ...p, subnet: e.target.value }))} required />
            <Input data-testid="subvendo-gateway-input" placeholder="Gateway" value={form.gateway} onChange={(e) => setForm((p) => ({ ...p, gateway: e.target.value }))} required />
            <Input data-testid="subvendo-dns-input" placeholder="DNS list" value={form.dns} onChange={(e) => setForm((p) => ({ ...p, dns: e.target.value }))} required />
            <Input data-testid="subvendo-interface-input" placeholder="Interface alias" value={form.interface_name} onChange={(e) => setForm((p) => ({ ...p, interface_name: e.target.value }))} required />
            <Input data-testid="subvendo-parent-interface-input" placeholder="Parent NIC" value={form.parent_interface} onChange={(e) => setForm((p) => ({ ...p, parent_interface: e.target.value }))} required />
            <Input data-testid="subvendo-rate-input" type="number" placeholder="Rate kbps" value={form.rate_limit_kbps} onChange={(e) => setForm((p) => ({ ...p, rate_limit_kbps: e.target.value }))} required />
            <Button data-testid="create-subvendo-submit-button" type="submit" className="md:col-span-2 xl:col-span-4">Add sub-vendo</Button>
          </form>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="subvendo-card-list">
        {subvendos.map((sv) => (
          <Card key={sv.id} data-testid={`subvendo-card-${sv.id}`}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between" data-testid={`subvendo-title-${sv.id}`}>
                <span>{sv.name}</span>
                <span className="mono-data text-sm">VLAN {sv.vlan_id}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm" data-testid={`subvendo-subnet-${sv.id}`}>Subnet: <span className="mono-data">{sv.subnet}</span></p>
              <p className="text-sm" data-testid={`subvendo-gateway-${sv.id}`}>Gateway: <span className="mono-data">{sv.gateway}</span></p>
              <p className="text-sm" data-testid={`subvendo-rate-${sv.id}`}>Rate: <span className="mono-data">{sv.rate_limit_kbps} kbps</span></p>
              <Button data-testid={`subvendo-delete-button-${sv.id}`} variant="destructive" onClick={() => removeSubvendo(sv.id)}>Delete</Button>
            </CardContent>
          </Card>
        ))}
        {subvendos.length === 0 && (
          <Card data-testid="subvendo-empty-state-card">
            <CardContent className="p-6 text-sm text-muted-foreground" data-testid="subvendo-empty-state">
              No VLAN sub-vendo configured yet.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
