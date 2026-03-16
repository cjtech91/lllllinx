import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, getErrorMessage } from "@/lib/api";

export default function ConfigPage() {
  const [script, setScript] = useState("");
  const [generatedAt, setGeneratedAt] = useState("");

  const loadConfig = async () => {
    try {
      const response = await api.get("/config/export");
      setScript(response.data.script || "");
      setGeneratedAt(response.data.generated_at || "");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load config export"));
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const copyScript = async () => {
    try {
      await navigator.clipboard.writeText(script);
      toast.success("Linux config script copied");
    } catch (_error) {
      toast.error("Clipboard copy failed");
    }
  };

  return (
    <div className="space-y-6" data-testid="config-page">
      <Card data-testid="config-export-card">
        <CardHeader>
          <CardTitle data-testid="config-export-title">Linux VLAN + QoS Config Generator</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground" data-testid="config-generated-time">
            Generated at: {generatedAt ? new Date(generatedAt).toLocaleString() : "..."}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button data-testid="config-refresh-button" onClick={loadConfig}>Refresh Script</Button>
            <Button data-testid="config-copy-button" variant="secondary" onClick={copyScript}>Copy to Clipboard</Button>
          </div>
          <textarea
            data-testid="config-script-textarea"
            className="w-full h-[420px] rounded-md border border-input bg-background p-3 text-xs mono-data"
            value={script}
            readOnly
          />
        </CardContent>
      </Card>
    </div>
  );
}
