import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatusPill from "@/components/StatusPill";
import { api } from "@/lib/api";
import { useAppState } from "@/lib/store";

/**
 * Reverse logistics — one origin (a distribution center), several
 * candidate destinations, ranked by the AI decision engine's
 * /decision/logistics endpoint. Matches the preview's rank-list layout.
 */

function scoreTone(score) {
  if (score >= 75) return "teal";
  if (score >= 50) return "amber";
  return "red";
}

export default function ReverseLogisticsPage() {
  const { logDecision } = useAppState();
  const [origin, setOrigin] = useState("");
  const [destinationsDraft, setDestinationsDraft] = useState("");
  const [ranking, setRanking] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ranOrigin, setRanOrigin] = useState("");

  const run = async () => {
    const destinations = destinationsDraft
      .split("\n")
      .map((d) => d.trim())
      .filter(Boolean);
    if (!origin.trim() || destinations.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      const result = await api.decideLogistics(origin.trim(), destinations);
      setRanking(result);
      setRanOrigin(origin.trim());
      const top = result.ranking?.[0];
      logDecision({
        type: "logistics",
        address: origin.trim(),
        destinations,
        topDestination: top?.address,
        score: top?.overall_score,
        summary: top
          ? `Reverse logistics · top pick ${top.address} (score ${top.overall_score})`
          : "Reverse logistics · ranked",
      });
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const factorValue = (row, key) => row.factors?.find((f) => f.factor === key)?.score;

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-5 space-y-3">
          <div className="text-sm font-semibold text-slate-100">Reverse logistics</div>
          <div className="text-[11px] text-slate-500">
            Rank candidate destinations from a distribution center by combined accessibility,
            infrastructure, and hazard-safety score — calls POST /decision/logistics.
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr] gap-3 pt-1">
            <div>
              <label className="text-[10px] font-mono uppercase text-slate-500 mb-1 block">
                Origin (distribution center)
              </label>
              <input
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="900 W Fulton Market, Chicago, IL"
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-2 text-xs text-slate-200 placeholder:text-slate-600 outline-none focus:border-teal-700"
              />
            </div>
            <div>
              <label className="text-[10px] font-mono uppercase text-slate-500 mb-1 block">
                Destinations (one per line)
              </label>
              <textarea
                value={destinationsDraft}
                onChange={(e) => setDestinationsDraft(e.target.value)}
                placeholder={"Indianapolis, IN\nColumbus, OH\nLouisville, KY"}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-2 text-xs text-slate-200 placeholder:text-slate-600 outline-none focus:border-teal-700 resize-none"
              />
            </div>
          </div>
          <Button
            onClick={run}
            disabled={loading}
            className="bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs"
          >
            {loading ? "Ranking…" : "Rank destinations"}
          </Button>
          {error && <div className="text-xs text-red-400 font-mono">{error.message}</div>}
        </CardContent>
      </Card>

      {ranking && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-0">
            <div className="px-5 pt-4 pb-2 text-[11px] text-slate-500">
              Origin: <span className="text-slate-300">{ranOrigin}</span>. Ranked by combined
              score across accessibility, infrastructure, and hazard safety.
            </div>
            <div className="grid grid-cols-[32px_1.4fr_.7fr_.7fr_.7fr] gap-3 px-5 py-2 text-[10px] font-mono uppercase tracking-wide text-slate-500 border-t border-b border-slate-800">
              <span>#</span>
              <span>Destination</span>
              <span>Score</span>
              <span>Access.</span>
              <span>Infra.</span>
            </div>
            {ranking.ranking?.map((row, i) => (
              <div
                key={row.address}
                className={`grid grid-cols-[32px_1.4fr_.7fr_.7fr_.7fr] gap-3 items-center px-5 py-3 text-xs ${
                  i !== ranking.ranking.length - 1 ? "border-b border-slate-800/60" : ""
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-md flex items-center justify-center text-[11px] font-mono font-bold ${
                    i === 0 ? "bg-teal-950 text-teal-400" : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {row.rank ?? i + 1}
                </span>
                <span className="font-semibold text-slate-100">{row.address}</span>
                <span>
                  <StatusPill tone={scoreTone(row.overall_score)}>{row.overall_score}</StatusPill>
                </span>
                <span className="font-mono text-slate-400">
                  {factorValue(row, "accessibility") ?? "—"}
                </span>
                <span className="font-mono text-slate-400">
                  {factorValue(row, "infrastructure") ?? "—"}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
