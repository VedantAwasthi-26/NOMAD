import { useEffect, useState } from "react";
import { X, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAppState } from "@/lib/store";

/**
 * Location Comparison — a card per saved site, each scored via
 * /decision/feasibility, with a remove button (top-right of the card,
 * matching the preview's compare-col-remove) that drops it from the
 * watchlist entirely. A dashed "add site" card at the end adds the
 * current address bar value straight into the comparison.
 */

const FACTOR_ORDER = [
  { key: "accessibility", label: "Accessibility" },
  { key: "demand", label: "Demand" },
  { key: "regulatory_fit", label: "Regulatory fit" },
  { key: "infrastructure", label: "Infrastructure" },
  { key: "hazard_safety", label: "Hazard safety" },
];

function barTone(value) {
  if (value >= 75) return "bg-teal-400";
  if (value >= 50) return "bg-amber-400";
  return "bg-red-400";
}

export default function ComparePage() {
  const { watchlist, removeFromWatchlist, addToWatchlist, activeAddress } = useAppState();
  const [results, setResults] = useState({});
  const [draft, setDraft] = useState("");

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

  const factorsFor = (rec) => {
    if (!rec) return [];
    const byKey = Object.fromEntries((rec.factor_breakdown || []).map((f) => [f.factor, f]));
    return FACTOR_ORDER.map(({ key, label }) => ({
      label,
      value: byKey[key]?.score ?? null,
    }));
  };

  const addDraft = () => {
    const trimmed = (draft || activeAddress || "").trim();
    if (!trimmed) return;
    addToWatchlist(trimmed);
    setDraft("");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Location Comparison</h1>
        <p className="text-xs font-mono text-slate-500 mt-1">
          {watchlist.length} candidate{watchlist.length === 1 ? "" : "s"}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {watchlist.map((w) => {
          const rec = results[w.address];
          const factors = factorsFor(rec);
          return (
            <Card key={w.id} className="bg-slate-900 border-slate-800 relative overflow-hidden">
              <button
                onClick={() => removeFromWatchlist(w.id)}
                aria-label={`Remove ${w.address} from comparison`}
                className="absolute top-2.5 right-2.5 z-10 w-6 h-6 rounded-md border border-slate-700 bg-slate-950/80 flex items-center justify-center text-slate-500 hover:text-red-400 hover:border-red-900 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>

              <div className="px-4 pt-7 pb-4 border-b border-slate-800 text-center">
                <div className="text-3xl font-bold text-slate-50">
                  {rec ? rec.overall_score : "…"}
                </div>
                <div className="text-[11px] text-slate-500 mt-1.5 truncate" title={w.address}>
                  {w.address}
                </div>
              </div>

              <CardContent className="pt-3.5 pb-4 px-4 space-y-0">
                {factors.map((f, i) => (
                  <div
                    key={f.label}
                    className={`grid grid-cols-[92px_1fr_28px] items-center gap-2.5 py-2 ${i !== 0 ? "border-t border-slate-800/60" : ""}`}
                  >
                    <span className="text-[11px] text-slate-300">{f.label}</span>
                    <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${barTone(f.value ?? 0)}`}
                        style={{ width: `${f.value ?? 0}%` }}
                      />
                    </div>
                    <span className="text-[11px] font-mono text-slate-400 text-right">
                      {f.value ?? "—"}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}

        <div className="border border-dashed border-slate-800 rounded-lg flex flex-col items-center justify-center gap-2.5 min-h-[280px] p-5 text-center">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Address to add…"
            className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 w-full outline-none focus:border-teal-700"
            onKeyDown={(e) => e.key === "Enter" && addDraft()}
          />
          <button
            onClick={addDraft}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-teal-400 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Add another site to compare
          </button>
        </div>
      </div>

      {watchlist.length === 0 && (
        <div className="text-xs text-slate-500 font-mono px-1">
          No sites saved yet — add one above, or save addresses from the Feasibility page.
        </div>
      )}
    </div>
  );
}
