import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function ReportsPage() {
  const [report, setReport] = useState({ totals: {}, by_subvendo: [], trend: [] });
  const [chartWidth, setChartWidth] = useState(900);

  const loadReports = async () => {
    const response = await api.get("/reports/sales");
    setReport(response.data);
  };

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    const updateWidth = () => {
      const candidate = window.innerWidth - 420;
      setChartWidth(Math.max(320, candidate));
    };
    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  return (
    <div className="space-y-6" data-testid="reports-page">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card data-testid="report-total-revenue-card">
          <CardHeader><CardTitle data-testid="report-total-revenue-title">Total Revenue</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-semibold mono-data" data-testid="report-total-revenue-value">₱{report.totals.revenue ?? 0}</p></CardContent>
        </Card>
        <Card data-testid="report-total-transactions-card">
          <CardHeader><CardTitle data-testid="report-total-transactions-title">Transactions</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-semibold mono-data" data-testid="report-total-transactions-value">{report.totals.transactions ?? 0}</p></CardContent>
        </Card>
        <Card data-testid="report-total-minutes-card">
          <CardHeader><CardTitle data-testid="report-total-minutes-title">Minutes Sold</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-semibold mono-data" data-testid="report-total-minutes-value">{report.totals.minutes ?? 0}</p></CardContent>
        </Card>
      </div>

      <Card data-testid="revenue-trend-card">
        <CardHeader><CardTitle data-testid="revenue-trend-title">Revenue Trend (Last 7 Days)</CardTitle></CardHeader>
        <CardContent>
          <div className="w-full overflow-x-auto" data-testid="revenue-trend-chart-wrapper">
            <BarChart width={chartWidth} height={300} data={report.trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="revenue" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
            </BarChart>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="subvendo-report-card">
        <CardHeader><CardTitle data-testid="subvendo-report-title">Per Sub-Vendo Sales</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2" data-testid="subvendo-report-list">
            {(report.by_subvendo || []).map((row) => (
              <div key={row.name} className="rounded-md border p-3 flex items-center justify-between" data-testid={`subvendo-report-item-${row.name.toLowerCase().replace(/\s+/g, "-")}`}>
                <div>
                  <p className="font-medium">{row.name}</p>
                  <p className="text-xs text-muted-foreground mono-data">{row.transactions} tx / {row.minutes} mins</p>
                </div>
                <p className="mono-data font-semibold">₱{row.revenue}</p>
              </div>
            ))}
            {(report.by_subvendo || []).length === 0 && (
              <p className="text-sm text-muted-foreground" data-testid="subvendo-report-empty-state">No sales data yet.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
