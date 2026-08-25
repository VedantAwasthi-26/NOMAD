import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatusPill from "@/components/StatusPill";
import StatCard from "@/components/StatCard";
import AddressBar from "@/components/AddressBar";
import { api, USE_MOCK } from "@/lib/api";
import { useAppState } from "@/lib/store";
import {
  Building2,
  Network,
  ShieldAlert,
  Database,
  Settings as SettingsIcon,
  ChevronRight,
  CheckCircle2,
} from "lucide-react";

function verdictTone(score) {
  if (score >= 75) return "teal";
  if (score >= 50) return "amber";
  return "red";
}

export default function OverviewPage() {
  const navigate = useNavigate();
  const { watchlist, activeAddress } = useAppState();

  // Score every saved address via the AI decision engine so this page
  // reflects real runs instead of a fabricated decision log.
  const [results, setResults] = useState({});
  useEffect(() => {
    let cancelled = false;
    watchlist.forEach((w) => {
      if (results[w.address]) return;
      api.decideFeasibility(w.address).then((r) => {
        if (!cancelled) setResults((prev) => ({ ...prev, [w.address]: r }));
      }).catch(() => {});
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchlist]);

  const scored = watchlist.map((w) => ({ ...w, rec: results[w.address] })).filter((w) => w.rec);
  const pendingCount = watchlist.length - scored.length;
  const openRisks = scored.filter((w) => w.rec.flagged_gaps?.length > 0).length;
  const recommended = scored.filter((w) => w.rec.feasible).length;

  const modules = [
    { title: "Site & Facility Feasibility", path: "/feasibility", icon: Building2 },
    { title: "Multi-Location Operations Monitor", path: "/network", icon: Network },
    { title: "Regulatory, Zoning & Hazard Research", path: "/risk", icon: ShieldAlert },
    { title: "Data Quality & Coverage", path: "/data-sources", icon: Database },
    { title: "System Settings", path: "/settings", icon: SettingsIcon },
  ];

  return (
    <div className="space-y-8">
      <div className="max-w-xl">
        <div className="text-[11px] font-mono uppercase tracking-widest text-teal-400 mb-3 flex items-center gap-2">
          <span className="w-4 h-px bg-teal-400" /> Overview
        </div>
        <h1 className="text-3xl font-bold text-slate-50 mb-3 leading-tight">
          Make better decisions about your physical operations.
        </h1>
        <p className="text-slate-400 text-sm leading-relaxed mb-5">
          Mireye connects physical-world intelligence with business requirements to
          recommend where to expand and which site to choose.
        </p>
        <div className="flex gap-3">
          <Button
            onClick={() => navigate("/feasibility")}
            className="bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold"
          >
            Start a decision <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate("/network")}
            className="border-slate-700 text-slate-200"
          >
            View locations
          </Button>
        </div>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <AddressBar />
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Saved locations" value={watchlist.length} delta="in your watchlist" tone="teal" />
        <StatCard label="Sites scored" value={scored.length} delta={`${pendingCount} pending`} />
        <StatCard label="Flagged gaps" value={openRisks} delta="from decision engine" tone={openRisks ? "amber" : "teal"} />
        <StatCard label="Recommended" value={recommended} delta="feasible: true" tone="teal" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-4">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-semibold text-slate-100">Decisions</CardTitle>
            <button onClick={() => navigate("/feasibility")} className="text-xs font-mono text-teal-400">
              View all →
            </button>
          </CardHeader>
          <CardContent className="pt-0 divide-y divide-slate-800">
            {scored.length === 0 ? (
              <div className="text-xs text-slate-500 font-mono py-3">
                No addresses scored yet — save one from the field above.
              </div>
            ) : (
              scored.map((w) => (
                <div key={w.id} className="flex items-center justify-between py-3 first:pt-0">
                  <div>
                    <div className="text-sm font-semibold text-slate-100">{w.address}</div>
                    <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                      Feasibility · score {w.rec.overall_score}
                    </div>
                  </div>
                  <StatusPill tone={verdictTone(w.rec.overall_score)}>
                    {w.rec.feasible ? "Recommended" : "Attention required"}
                  </StatusPill>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-100">Operating posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-500 mb-1">Active address</div>
              <div className="text-sm text-slate-200 break-words">{activeAddress || "none selected"}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-500 mb-1">Backend mode</div>
              <div className="text-sm text-slate-200">{USE_MOCK ? "Mock data (backend not connected)" : "Live backend"}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-slate-100 mb-1">Modules</h4>
        <p className="text-xs text-slate-500 mb-4">Click a module to open its live page.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {modules.map((m) => (
            <button
              key={m.title}
              onClick={() => navigate(m.path)}
              className="text-left bg-slate-900 border border-slate-800 hover:border-teal-700 rounded-lg p-4 transition-colors group"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="w-8 h-8 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center">
                  <m.icon className="w-4 h-4 text-teal-400" />
                </div>
                <StatusPill tone="teal">Live</StatusPill>
              </div>
              <div className="text-sm font-semibold text-slate-100 group-hover:text-teal-400">
                {m.title}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
