import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatusPill from "@/components/StatusPill";
import { useAppState } from "@/lib/store";
import { Building2, Route as RouteIcon, Trash2 } from "lucide-react";

/**
 * A log of every decision actually run against the real backend —
 * feasibility scores, reverse-logistics rankings. Recorded by
 * FeasibilityPage / ReverseLogisticsPage via logDecision(), not
 * fabricated here.
 */

function verdictTone(score) {
  if (score >= 75) return "teal";
  if (score >= 50) return "amber";
  return "red";
}

function formatWhen(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistoryPage() {
  const { history, clearHistory, setActiveAddress } = useAppState();
  const navigate = useNavigate();

  const reopen = (entry) => {
    if (entry.type === "feasibility") {
      setActiveAddress(entry.address);
      navigate("/feasibility");
    } else if (entry.type === "logistics") {
      navigate("/logistics");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">History</h1>
          <p className="text-xs font-mono text-slate-500 mt-1">
            {history.length} decision{history.length === 1 ? "" : "s"} run this session
          </p>
        </div>
        {history.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearHistory}
            className="border-slate-700 text-slate-400 hover:text-red-400 hover:border-red-900 text-xs"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Clear history
          </Button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="text-xs text-slate-500 font-mono px-1">
          No decisions run yet — analyze a site on Feasibility or rank destinations on Reverse
          Logistics, and it'll show up here.
        </div>
      ) : (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-0 divide-y divide-slate-800">
            {history.map((entry) => {
              const Icon = entry.type === "logistics" ? RouteIcon : Building2;
              return (
                <button
                  key={entry.id}
                  onClick={() => reopen(entry)}
                  className="w-full text-left flex items-center gap-3.5 px-5 py-4 hover:bg-slate-800/40 transition-colors"
                >
                  <div className="w-8 h-8 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4 text-teal-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-slate-100 truncate">
                      {entry.address}
                    </div>
                    <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                      {entry.summary} · {formatWhen(entry.at)}
                    </div>
                  </div>
                  {typeof entry.score === "number" && (
                    <StatusPill tone={verdictTone(entry.score)}>{entry.score}</StatusPill>
                  )}
                </button>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
