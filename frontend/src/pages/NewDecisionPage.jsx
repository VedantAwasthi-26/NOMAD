import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Building2, Columns3, Route as RouteIcon, ChevronRight } from "lucide-react";

/**
 * Landing page for starting a new decision — routes into whichever
 * real analysis the user actually wants, rather than guessing which
 * page they meant to land on.
 */

const OPTIONS = [
  {
    icon: Building2,
    title: "Site Feasibility",
    description:
      "Score a single candidate address — accessibility, hazard safety, regulatory fit, and demand.",
    path: "/feasibility",
  },
  {
    icon: Columns3,
    title: "Compare sites",
    description:
      "Weigh several saved addresses side-by-side using the same scored factors.",
    path: "/compare",
  },
  {
    icon: RouteIcon,
    title: "Reverse logistics",
    description:
      "Rank candidate destinations from a distribution center by accessibility and infrastructure.",
    path: "/logistics",
  },
];

export default function NewDecisionPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">New decision</h1>
        <p className="text-xs font-mono text-slate-500 mt-1">
          What are you trying to decide?
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        {OPTIONS.map((opt) => (
          <button
            key={opt.path}
            onClick={() => navigate(opt.path)}
            className="text-left"
          >
            <Card className="bg-slate-900 border-slate-800 hover:border-teal-700 transition-colors h-full p-5 flex flex-col gap-3">
              <div className="w-9 h-9 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center">
                <opt.icon className="w-4 h-4 text-teal-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-100 flex items-center gap-1">
                  {opt.title} <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
                </div>
                <div className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                  {opt.description}
                </div>
              </div>
            </Card>
          </button>
        ))}
      </div>
    </div>
  );
}
