import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatusPill from "@/components/StatusPill";
import MapView from "@/components/MapView";
import AddressBar from "@/components/AddressBar";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useApi";
import { useAppState } from "@/lib/store";
import { CheckCircle2, XCircle } from "lucide-react";

const AGENT_LABELS = {
  hazard_safety: { name: "Risk & Monitoring Agent", role: "hazard_safety" },
  accessibility: { name: "Logistics & Network Agent", role: "accessibility" },
  regulatory_fit: { name: "Regulatory & Compliance Agent", role: "regulatory_fit" },
  demand: { name: "Demand & Market Agent", role: "demand" },
};

function verdictTone(score) {
  if (score >= 75) return "teal";
  if (score >= 50) return "amber";
  return "red";
}

export default function FeasibilityPage() {
  const { activeAddress, watchlist, logDecision } = useAppState();

  // Raw evidence — Vedant's /feasibility/ bucket (lat/lng + factors, no
  // scoring/explanation).
  const { data: raw, loading: rawLoading, error: rawError } = useAsync(
    (signal) => api.getFeasibility(activeAddress, signal),
    [activeAddress],
    { enabled: !!activeAddress }
  );

  // AI-scored verdict — /decision/feasibility, the Recommendation contract.
  const { data: rec, loading: recLoading, error: recError } = useAsync(
    (signal) => api.decideFeasibility(activeAddress, signal),
    [activeAddress],
    { enabled: !!activeAddress }
  );

  // Every completed feasibility run is a real decision — log it so it
  // shows up in History and on the Overview "Decisions" list.
  useEffect(() => {
    if (!rec) return;
    logDecision({
      type: "feasibility",
      address: rec.address,
      score: rec.overall_score,
      feasible: rec.feasible,
      summary: `Feasibility · score ${rec.overall_score}`,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rec]);

  const mapSites = activeAddress && raw
    ? [{ id: activeAddress, name: activeAddress, lat: raw.lat, lng: raw.lng, score: rec?.overall_score, tone: rec ? verdictTone(rec.overall_score) : "slate" }]
    : [];

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <AddressBar />
        </CardContent>
      </Card>

      {!activeAddress && (
        <div className="text-xs text-slate-500 font-mono px-1">
          Enter an address above and hit Analyze — this calls the backend's
          /feasibility/ and /decision/feasibility endpoints for that exact address.
        </div>
      )}

      {activeAddress && (
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
          <Card className="bg-slate-900 border-slate-800 h-fit">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-100">Site Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <div className="text-[10px] font-mono uppercase text-slate-500 mb-1.5">Address</div>
                <div className="text-xs text-slate-300 break-words">{activeAddress}</div>
                {raw && (
                  <div className="text-[10px] font-mono text-teal-500 mt-1.5">
                    resolved · {raw.lat.toFixed(4)}, {raw.lng.toFixed(4)}
                  </div>
                )}
              </div>
              {rawError && (
                <div className="text-[10px] font-mono text-red-400">{rawError.message}</div>
              )}
              {raw && (
                <div>
                  <div className="text-[10px] font-mono uppercase text-slate-500 mb-1.5">Raw factors</div>
                  <div className="space-y-1">
                    {Object.entries(raw.factors || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-[11px]">
                        <span className="text-slate-500 font-mono">{k}</span>
                        <span className="text-slate-300">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {raw?.blockers?.length > 0 && (
                <div>
                  <div className="text-[10px] font-mono uppercase text-red-400 mb-1.5">Blockers</div>
                  <ul className="text-[11px] text-red-400 space-y-1">
                    {raw.blockers.map((b) => (
                      <li key={b}>· {b}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card className="bg-slate-900 border-slate-800 overflow-hidden">
              {rawError ? (
                <div className="h-52 flex items-center justify-center text-xs text-red-400 font-mono px-4 text-center">
                  Couldn't load site map — check API connection
                </div>
              ) : (
                <MapView sites={rawLoading ? [] : mapSites} height="13rem" />
              )}
            </Card>

            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-slate-100">AI Decision Engine verdict</CardTitle>
                <div className="text-[10px] font-mono text-slate-500">POST /decision/feasibility</div>
              </CardHeader>
              <CardContent>
                {recLoading && <div className="text-xs text-slate-500 font-mono">Scoring…</div>}
                {recError && <div className="text-xs text-red-400 font-mono">{recError.message}</div>}
                {rec && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <div className="text-4xl font-bold text-slate-50">{rec.overall_score}</div>
                      <div>
                        <StatusPill tone={verdictTone(rec.overall_score)}>
                          {rec.feasible ? "Feasible" : "Not recommended"}
                        </StatusPill>
                        <div className="text-[10px] font-mono text-slate-500 mt-1">
                          confidence {(rec.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                    {rec.explanation && (
                      <p className="text-xs text-slate-400 leading-relaxed">{rec.explanation}</p>
                    )}
                    {rec.strengths?.length > 0 && (
                      <ul className="text-xs text-slate-400 space-y-1">
                        {rec.strengths.map((s) => (
                          <li key={s} className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 shrink-0" /> {s}
                          </li>
                        ))}
                      </ul>
                    )}
                    {rec.flagged_gaps?.length > 0 && (
                      <ul className="text-xs text-amber-400 space-y-1">
                        {rec.flagged_gaps.map((g) => (
                          <li key={g.field} className="flex items-center gap-1.5">
                            <XCircle className="w-3.5 h-3.5 shrink-0" /> {g.field} — {g.reason}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {activeAddress && rec && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-100">Factor breakdown</CardTitle>
            <div className="text-[10px] font-mono text-slate-500">
              from the 5-agent decision engine — each row is one agent's scored factor
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-0">
            {rec.factor_breakdown.map((f) => {
              const meta = AGENT_LABELS[f.factor] || { name: f.factor, role: f.source_system };
              return (
                <div key={f.factor} className="border border-slate-800 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="text-xs font-semibold text-slate-100">{meta.name}</div>
                    <div className="text-xs font-mono text-teal-400">{f.score}</div>
                  </div>
                  <div className="text-[10px] text-slate-500 mb-1">
                    {f.factor} · weight {(f.weight * 100).toFixed(0)}% · conf {(f.confidence * 100).toFixed(0)}%
                  </div>
                  {f.note && <div className="text-[10px] font-mono text-amber-400">{f.note}</div>}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {watchlist.length > 0 && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4 flex items-center justify-between gap-3">
            <div className="text-xs text-slate-400">
              {watchlist.length} site{watchlist.length === 1 ? "" : "s"} saved — see them
              side-by-side on the Compare page.
            </div>
            <Link
              to="/compare"
              className="text-xs font-semibold text-teal-400 hover:text-teal-300 whitespace-nowrap"
            >
              Open Compare →
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
