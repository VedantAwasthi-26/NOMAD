import { Card, CardContent } from "@/components/ui/card";

export default function StatCard({ label, value, delta, tone = "slate" }) {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="p-5">
        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2">
          {label}
        </div>
        <div className="text-3xl font-bold text-slate-50 mb-1">{value}</div>
        <div
          className={`text-xs ${
            tone === "amber" ? "text-amber-400" : tone === "teal" ? "text-teal-400" : "text-slate-400"
          }`}
        >
          {delta}
        </div>
      </CardContent>
    </Card>
  );
}
