import { useEffect, useState } from "react";
import { Cpu, HardDrive, Thermometer } from "lucide-react";
import { api } from "@/lib/api";

export const StatusWidget = () => {
  const [status, setStatus] = useState(null);

  const loadStatus = async () => {
    try {
      const response = await api.get("/system/status");
      setStatus(response.data);
    } catch (error) {
      console.error("status widget error", error);
    }
  };

  useEffect(() => {
    loadStatus();
    const timer = setInterval(loadStatus, 8000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card px-3 py-2"
      data-testid="system-status-widget"
    >
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground" data-testid="system-status-board">
        <Cpu className="h-3.5 w-3.5" />
        {status?.board_label || "Loading board..."}
      </div>
      <div className="h-4 w-px bg-border" />
      <div className="flex items-center gap-1 text-xs mono-data" data-testid="system-status-cpu-load">
        <Cpu className="h-3.5 w-3.5 text-primary" />
        CPU: {status?.cpu_load_1m ?? "--"}
      </div>
      <div className="flex items-center gap-1 text-xs mono-data" data-testid="system-status-memory">
        <HardDrive className="h-3.5 w-3.5 text-primary" />
        RAM: {status?.memory_usage_percent ?? "--"}%
      </div>
      <div className="flex items-center gap-1 text-xs mono-data" data-testid="system-status-temp">
        <Thermometer className="h-3.5 w-3.5 text-primary" />
        TEMP: {status?.cpu_temp_c ?? "--"}°C
      </div>
    </div>
  );
};
