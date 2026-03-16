import { useEffect, useState } from "react";
import { CirclePower, Coins, Layers, Ticket } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const MetricCard = ({ title, value, icon: Icon, testid }) => (
  <Card className="metric-card" data-testid={`${testid}-card`}>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium" data-testid={`${testid}-title`}>{title}</CardTitle>
      <Icon className="h-4 w-4 text-primary" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-semibold mono-data" data-testid={testid}>{value}</div>
    </CardContent>
  </Card>
);

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);

  const loadSummary = async () => {
    const response = await api.get("/dashboard/summary");
    setSummary(response.data);
  };

  useEffect(() => {
    loadSummary();
    const interval = setInterval(loadSummary, 12000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6" data-testid="dashboard-metrics-grid">
        <MetricCard title="Sub-Vendo VLANs" value={summary?.subvendo_count ?? "0"} icon={Layers} testid="metric-subvendo-count" />
        <MetricCard title="Unused PINs" value={summary?.vouchers?.unused ?? "0"} icon={Ticket} testid="metric-unused-pins" />
        <MetricCard title="Sales Today" value={`₱${summary?.sales_today ?? "0"}`} icon={Coins} testid="metric-sales-today" />
        <MetricCard title="Relay State" value={summary?.relay_on ? "ON" : "OFF"} icon={CirclePower} testid="metric-relay-state" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6" data-testid="dashboard-bento-grid">
        <Card className="xl:col-span-3" data-testid="voucher-health-card">
          <CardHeader>
            <CardTitle data-testid="voucher-health-title">Voucher Health Snapshot</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-lg border bg-secondary/40 p-4" data-testid="voucher-total-block">
                <p className="text-xs uppercase text-muted-foreground">Total</p>
                <p className="text-2xl font-semibold mono-data" data-testid="voucher-total-value">{summary?.vouchers?.total ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-secondary/40 p-4" data-testid="voucher-active-block">
                <p className="text-xs uppercase text-muted-foreground">Active</p>
                <p className="text-2xl font-semibold mono-data" data-testid="voucher-active-value">{summary?.vouchers?.active ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-secondary/40 p-4" data-testid="voucher-expired-block">
                <p className="text-xs uppercase text-muted-foreground">Expired</p>
                <p className="text-2xl font-semibold mono-data" data-testid="voucher-expired-value">{summary?.vouchers?.expired ?? 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="board-profile-card">
          <CardHeader>
            <CardTitle data-testid="board-profile-title">Hardware Runtime</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs uppercase text-muted-foreground">Active board profile</p>
            <p className="text-sm font-semibold mono-data" data-testid="board-profile-value">
              {summary?.board_profile || "loading"}
            </p>
            <p className="text-xs text-muted-foreground" data-testid="cpu-load-quick-value">
              CPU 1m Load: <span className="mono-data">{summary?.cpu_load_1m ?? "--"}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      <Card data-testid="top-subvendos-card">
        <CardHeader>
          <CardTitle data-testid="top-subvendos-title">Top Sub-Vendo Revenue</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2" data-testid="top-subvendos-list">
            {(summary?.top_subvendos || []).length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="top-subvendos-empty">No sales yet.</p>
            ) : (
              summary.top_subvendos.map((item) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-md border p-3"
                  data-testid={`top-subvendo-item-${item.name.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  <span className="font-medium">{item.name}</span>
                  <span className="mono-data">₱{item.revenue}</span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
