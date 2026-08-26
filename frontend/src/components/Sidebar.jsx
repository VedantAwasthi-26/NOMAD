import { NavLink } from "react-router-dom";
import { NAV } from "@/data/nav";

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-slate-800 bg-slate-950 flex flex-col sticky top-0 h-screen z-40">
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-slate-800">
        <div className="w-7 h-7 rounded-md border border-teal-500 flex items-center justify-center text-teal-400 font-bold text-xs shrink-0">
          N
        </div>
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-100 leading-tight truncate">
            NOMAD
          </div>
          <div className="text-[10px] font-mono text-slate-500 leading-tight truncate">
            Decision Intelligence
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV.map((n) => (
          <NavLink
            key={n.id}
            to={n.path}
            end={n.path === "/"}
            className={({ isActive }) =>
              `w-full flex items-center gap-2.5 text-xs font-mono px-3 py-2.5 rounded-md border-l-2 transition-colors ${
                isActive
                  ? "bg-slate-800 text-slate-100 border-teal-400"
                  : "border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-900"
              }`
            }
          >
            <n.icon className="w-3.5 h-3.5 shrink-0" />
            {n.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-slate-800 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-semibold text-slate-400 shrink-0">
          VA
        </div>
        <div className="text-[10px] text-slate-500 font-mono leading-tight">
          Analyst workspace
        </div>
      </div>
    </aside>
  );
}
