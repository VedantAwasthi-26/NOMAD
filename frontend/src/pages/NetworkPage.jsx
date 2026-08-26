import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatusPill from "@/components/StatusPill";
import StatCard from "@/components/StatCard";
import MapView from "@/components/MapView";
import AddressBar from "@/components/AddressBar";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useApi";
import { useAppState } from "@/lib/store";
import { ShieldAlert } from "lucide-react";

/**
 * Network Monitor = /multi-location/ over whatever addresses the user
 * has saved to their watchlist. There's no fixed "24 facilities" — the
 * fleet IS the watchlist.
 */
export default function NetworkPage() {
  const { watchlist } = useAppState();
  const addresses = watchlist.map((w) => w.address);

  const { data, loading, error } = useAsync(
    (signal) => api.getMultiLocation(addresses, signal),
    [addresses.join("|")],
    { enabled: addresses.length > 0 }
  );

  const locations = data?.locations || [];
  const mapSites = locations.map((l) => ({
    id: l.address,
    name: l.address,
    lat: l.lat,
    lng: l.lng,
    tone: l.fields?.status === "nominal" ? "teal" : "amber",
  }));

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4 space-y-2">
          <AddressBar />
          <div className="text-[10px] font-mono text-slate-500">
            Save addresses above to add them to the monitored network — this page calls
            POST /multi-location/ with every saved address.
          </div>
        </CardContent>
      </Card>

      {addresses.length === 0 ? (
        <div className="text-xs text-slate-500 font-mono px-1">
          No locations saved yet. Save at least one address to see it here.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatCard label="Locations monitored" value={locations.length} delta="from your watchlist" tone="teal" />
            <StatCard
              label="Outlier alerts"
              value={data?.outlier_alerts?.length ?? 0}
              tone={data?.outlier_alerts?.length ? "amber" : "slate"}
              delta="from comparative_metrics"
            />
            <StatCard
              label="Avg. uptime"
              value={data?.comparative_metrics?.avg_uptime_pct ? `${data.comparative_metrics.avg_uptime_pct}%` : "—"}
              delta="comparative_metrics.avg_uptime_pct"
            />
          </div>

          <Card className="bg-slate-900 border-slate-800 overflow-hidden">
            {error ? (
              <div className="h-56 flex items-center justify-center text-xs text-red-400 font-mono">
                Couldn't load facility map — {error.message}
              </div>
            ) : (
              <MapView sites={loading ? [] : mapSites} height="14rem" />
            )}
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.3fr] gap-4">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-slate-100">Outlier alerts</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(data?.outlier_alerts?.length ?? 0) === 0 ? (
                  <div className="text-xs text-slate-500 font-mono">No outliers flagged.</div>
                ) : (
                  data.outlier_alerts.map((a, i) => (
                    <div key={i} className="flex gap-3 border border-slate-800 rounded-lg p-3">
                      <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                      <div className="text-xs text-slate-300">{JSON.stringify(a)}</div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-slate-100">Locations</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800">
                      <th className="text-left font-mono font-normal py-2">Address</th>
                      <th className="text-right font-mono font-normal">Fields</th>
                      <th className="text-right font-mono font-normal">Data quality</th>
                    </tr>
                  </thead>
                  <tbody>
                    {locations.map((l) => (
                      <tr key={l.address} className="border-b border-slate-800/60 last:border-0">
                        <td className="py-2.5 text-slate-200">{l.address}</td>
                        <td className="text-right text-slate-400">{Object.keys(l.fields || {}).length}</td>
                        <td className="text-right">
                          <StatusPill tone={(l.data_quality?.length ?? 0) > 0 ? "teal" : "slate"}>
                            {l.data_quality?.length ?? 0} checked
                          </StatusPill>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
