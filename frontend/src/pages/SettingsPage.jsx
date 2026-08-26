import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import StatusPill from "@/components/StatusPill";
import { USE_MOCK } from "@/lib/api";

/**
 * The backend has no /settings endpoint (nothing to PUT to), so this
 * page shows the AI decision engine's actual, checked-in defaults —
 * app/engine/scoring.py's SITE_SELECTION_WEIGHTS / FEASIBILITY_WEIGHTS
 * and thresholds — instead of an invented, editable-looking form.
 */
const SITE_SELECTION_WEIGHTS = [
  { label: "Accessibility", value: 20 },
  { label: "Population coverage", value: 20 },
  { label: "Regulatory fit", value: 20 },
  { label: "Infrastructure", value: 20 },
  { label: "Hazard safety", value: 20 },
];

const FEASIBILITY_WEIGHTS = [
  { label: "Hazard safety", value: 45 },
  { label: "Accessibility", value: 30 },
  { label: "Infrastructure", value: 25 },
];

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-100">Site selection weights</CardTitle>
            <div className="text-[10px] font-mono text-slate-500">engine/scoring.py · SITE_SELECTION_WEIGHTS</div>
          </CardHeader>
          <CardContent className="space-y-4">
            {SITE_SELECTION_WEIGHTS.map((w) => (
              <div key={w.label}>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-300">{w.label}</span>
                  <span className="text-slate-500 font-mono">{w.value}%</span>
                </div>
                <Progress value={w.value} className="h-1.5 bg-slate-800" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-100">Feasibility weights</CardTitle>
            <div className="text-[10px] font-mono text-slate-500">engine/scoring.py · FEASIBILITY_WEIGHTS</div>
          </CardHeader>
          <CardContent className="space-y-4">
            {FEASIBILITY_WEIGHTS.map((w) => (
              <div key={w.label}>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-300">{w.label}</span>
                  <span className="text-slate-500 font-mono">{w.value}%</span>
                </div>
                <Progress value={w.value} className="h-1.5 bg-slate-800" />
              </div>
            ))}
            <div className="text-[10px] text-slate-500 pt-1">
              Only 3 of 5 site-selection factors apply pre-regulatory/demographic data,
              renormalized to sum to 100%.
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-slate-100">Decision thresholds</CardTitle>
          <div className="text-[10px] font-mono text-slate-500">engine/scoring.py</div>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="flex justify-between border-b border-slate-800 pb-2.5">
            <span className="text-slate-400">Feasibility pass threshold</span>
            <span className="text-slate-100 font-mono">55</span>
          </div>
          <div className="flex justify-between border-b border-slate-800 pb-2.5">
            <span className="text-slate-400">Hazard hard-floor threshold</span>
            <span className="text-slate-100 font-mono">50</span>
          </div>
          <div className="flex justify-between pb-1">
            <span className="text-slate-400">Hard-floor capped score</span>
            <span className="text-slate-100 font-mono">40</span>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-slate-100">Connection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="flex justify-between border-b border-slate-800 pb-2.5">
            <span className="text-slate-300">API base URL</span>
            <span className="text-slate-500 font-mono">{BASE_URL}</span>
          </div>
          <div className="flex justify-between pb-1">
            <span className="text-slate-300">Data mode</span>
            <StatusPill tone={USE_MOCK ? "amber" : "teal"}>{USE_MOCK ? "Mock data" : "Live backend"}</StatusPill>
          </div>
          <div className="text-[10px] text-slate-500 pt-1">
            Set VITE_API_BASE_URL and VITE_USE_MOCK_DATA=false in .env once the backend
            and AI decision-engine folders are merged in.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
