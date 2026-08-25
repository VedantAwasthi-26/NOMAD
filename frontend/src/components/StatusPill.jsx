export default function StatusPill({ tone = "slate", children }) {
  const tones = {
    teal: "bg-teal-500/10 text-teal-400 border-teal-500/30",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    red: "bg-red-500/10 text-red-400 border-red-500/30",
    violet: "bg-violet-500/10 text-violet-400 border-violet-500/30",
    slate: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  };
  return (
    <span
      className={`text-[10px] font-mono uppercase tracking-wide px-2 py-1 rounded-full border ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
