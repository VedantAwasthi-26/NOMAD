import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import StatusPill from "@/components/StatusPill";
import AddressBar from "@/components/AddressBar";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useApi";
import { useAppState } from "@/lib/store";

function riskTone(value) {
  if (value >= 60) return "red";
  if (value >= 35) return "amber";
  return "teal";
}

export default function RiskPage() {
  const { activeAddress } = useAppState();
  const [businessType, setBusinessType] = useState("warehouse");
  const [intendedUse, setIntendedUse] = useState("distribution");

  const { data: risk, loading: riskLoading, error: riskError } = useAsync(
    (signal) => api.getRisk(activeAddress, signal),
    [activeAddress],
    { enabled: !!activeAddress }
  );

  const { data: regulatory, loading: regLoading, error: regError } = useAsync(
    (signal) => api.getRegulatory(activeAddress, signal),
    [activeAddress],
    { enabled: !!activeAddress }
  );

  const { data: permits, loading: permitsLoading, error: permitsError } = useAsync(
    (signal) => api.getPermitResearch(activeAddress, businessType, intendedUse, signal),
    [activeAddress, businessType, intendedUse],
    { enabled: !!activeAddress }
  );

  const exposure = risk
    ? [
        { label: "Flood exposure", value: risk.environmental_risks?.flood_exposure_index ?? 0 },
        { label: "Wildfire exposure", value: risk.environmental_risks?.wildfire_exposure_index ?? 0 },
        { label: "Wind / storm exposure", value: risk.environmental_risks?.wind_storm_exposure_index ?? 0 },
      ]
    : [];

  const findings = regulatory
    ? [
        ...Object.entries(regulatory.regulations || {}).map(([k, v]) => ({ code: k, value: v, bucket: "regulations" })),
        ...Object.entries(regulatory.restrictions || {}).map(([k, v]) => ({ code: k, value: v, bucket: "restrictions" })),
        ...Object.entries(regulatory.environmental_constraints || {}).map(([k, v]) => ({ code: k, value: v, bucket: "environmental" })),
      ]
    : [];

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4 space-y-3">
          <AddressBar />
          <div className="flex gap-3 flex-wrap text-xs">
            <label className="flex items-center gap-2 text-slate-400">
              Business type
              <input
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 w-32"
              />
            </label>
            <label className="flex items-center gap-2 text-slate-400">
              Intended use
              <input
                value={intendedUse}
                onChange={(e) => setIntendedUse(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 w-36"
              />
            </label>
          </div>
        </CardContent>
      </Card>

      {!activeAddress ? (
        <div className="text-xs text-slate-500 font-mono px-1">
          Enter an address above — this calls /risk/, /regulatory/ and /permit-research/ for it.
        </div>
      ) : (
        <>
          {riskError && <div className="text-xs text-red-400 font-mono">{riskError.message}</div>}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {riskLoading && !risk
              ? [0, 1, 2].map((i) => (
                  <Card key={i} className="bg-slate-900 border-slate-800">
                    <CardContent className="p-5 text-xs text-slate-600 font-mono">Loading…</CardContent>
                  </Card>
                ))
              : exposure.map((e) => (
                  <Card key={e.label} className="bg-slate-900 border-slate-800">
                    <CardContent className="p-5">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2">{e.label}</div>
                      <div className="text-3xl font-bold text-slate-50 mb-2">{e.value}</div>
                      <Progress value={e.value} className="h-1.5 mb-2 bg-slate-800" />
                      <StatusPill tone={riskTone(e.value)}>
                        {e.value >= 60 ? "Elevated" : e.value >= 35 ? "Moderate" : "Low"} risk band
                      </StatusPill>
                    </CardContent>
                  </Card>
                ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-slate-100">Regulatory findings</CardTitle>
                <div className="text-[10px] font-mono text-slate-500">POST /regulatory/</div>
              </CardHeader>
              <CardContent className="space-y-3">
                {regError && <div className="text-xs text-red-400 font-mono">{regError.message}</div>}
                {regLoading && !regulatory && <div className="text-xs text-slate-500 font-mono">Loading…</div>}
                {findings.map((f) => (
                  <div key={`${f.bucket}-${f.code}`} className="flex items-start justify-between gap-3 border border-slate-800 rounded-lg p-3">
                    <div>
                      <div className="text-xs font-semibold text-slate-100">{f.code}</div>
                      <div className="text-[10px] font-mono text-slate-500 mt-1">{f.bucket}</div>
                    </div>
                    <StatusPill tone="slate">{String(f.value)}</StatusPill>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-slate-100">Permit tracker</CardTitle>
                <div className="text-[10px] font-mono text-slate-500">POST /permit-research/</div>
              </CardHeader>
              <CardContent className="space-y-3">
                {permitsError && <div className="text-xs text-red-400 font-mono">{permitsError.message}</div>}
                {permitsLoading && !permits && <div className="text-xs text-slate-500 font-mono">Loading…</div>}
                {permits &&
                  Object.entries(permits.permits || {}).map(([name, note]) => (
                    <div key={name} className="border border-slate-800 rounded-lg p-3">
                      <div className="text-xs font-semibold text-slate-100 capitalize">{name.replace(/_/g, " ")}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{String(note)}</div>
                    </div>
                  ))}
                {permits?.application_guidance && (
                  <div className="text-[10px] font-mono text-slate-500 pt-1">
                    est. {permits.application_guidance.estimated_days} days · {permits.application_guidance.agency}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
