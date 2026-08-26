import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatusPill from "@/components/StatusPill";
import StatCard from "@/components/StatCard";
import AddressBar from "@/components/AddressBar";
import { api, USE_MOCK } from "@/lib/api";
import { useAsync } from "@/lib/useApi";
import { useAppState } from "@/lib/store";

/**
 * "Data Sources" here means exactly what the backend can tell us about
 * itself: whether it's reachable, and the data_quality / partial_failures
 * arrays every Mireye-backed endpoint returns for the current address.
 * No invented vendor list — if a field failed to resolve, it shows up
 * here because the backend said so.
 */
export default function DataSourcesPage() {
  const { activeAddress } = useAppState();

  const { data: healthData, error: healthError } = useAsync((signal) => api.health(signal), []);

  const { data: verification, loading: vLoading, error: vError } = useAsync(
    (signal) => api.getVerification(activeAddress, signal),
    [activeAddress],
    { enabled: !!activeAddress }
  );

  const { data: context, loading: cLoading, error: cError } = useAsync(
    (signal) => api.getLocationContext(activeAddress, signal),
    [activeAddress],
    { enabled: !!activeAddress }
  );

  const backendUp = !!healthData && !healthError;
  const failures = verification?.partial_failures || [];
  const dataQuality = context?.data_quality || [];
  const resolvedFields = verification ? Object.keys(verification.fields || {}).length : 0;

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <AddressBar />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <StatCard
          label="Backend connectivity"
          value={backendUp ? "Online" : "Unreachable"}
          delta={USE_MOCK ? "mock mode — not calling a real backend" : "GET /locations/health"}
          tone={backendUp ? "teal" : "amber"}
        />
        <StatCard
          label="Fields resolved"
          value={activeAddress ? resolvedFields : "—"}
          delta="POST /verification/"
        />
        <StatCard
          label="Partial failures"
          value={activeAddress ? failures.length : "—"}
          tone={failures.length ? "amber" : "teal"}
          delta="verification.partial_failures"
        />
      </div>

      {!activeAddress ? (
        <div className="text-xs text-slate-500 font-mono px-1">
          Enter an address above to see live Mireye field coverage for it.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-100">Resolved fields</CardTitle>
              <div className="text-[10px] font-mono text-slate-500">verification.fields</div>
            </CardHeader>
            <CardContent className="space-y-2">
              {vError && <div className="text-xs text-red-400 font-mono">{vError.message}</div>}
              {vLoading && !verification && <div className="text-xs text-slate-500 font-mono">Loading…</div>}
              {verification &&
                Object.entries(verification.fields || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-[11px] border-b border-slate-800/60 pb-1.5">
                    <span className="text-slate-500 font-mono">{k}</span>
                    <span className="text-slate-300">{String(v)}</span>
                  </div>
                ))}
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-100">Data quality / gaps</CardTitle>
              <div className="text-[10px] font-mono text-slate-500">
                decision-engine.data_quality · verification.partial_failures
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {cError && <div className="text-xs text-red-400 font-mono">{cError.message}</div>}
              {cLoading && !context && <div className="text-xs text-slate-500 font-mono">Loading…</div>}
              {failures.length === 0 && dataQuality.length === 0 && !cLoading && (
                <div className="text-xs text-slate-500 font-mono">No gaps reported for this address.</div>
              )}
              {failures.map((f, i) => (
                <div key={`fail-${i}`} className="border border-amber-900/40 rounded-lg p-3">
                  <StatusPill tone="amber">partial failure</StatusPill>
                  <div className="text-[11px] text-slate-400 mt-1.5">{JSON.stringify(f)}</div>
                </div>
              ))}
              {dataQuality.map((q, i) => (
                <div key={`dq-${i}`} className="flex items-center justify-between border border-slate-800 rounded-lg p-3">
                  <div className="text-xs text-slate-200">{q.field ?? JSON.stringify(q)}</div>
                  {q.status && (
                    <StatusPill tone={q.status === "ok" ? "teal" : "amber"}>{q.status}</StatusPill>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
