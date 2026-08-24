import { useState } from "react";
import { Search, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/store";

/**
 * Every backend endpoint is address-driven, so this is the one input
 * that feeds the whole app. Typing an address here and hitting
 * "Analyze" sets the shared activeAddress — every page listens to it
 * and refetches automatically.
 */
export default function AddressBar({ compact = false }) {
  const { activeAddress, setActiveAddress, addToWatchlist } = useAppState();
  const [draft, setDraft] = useState(activeAddress || "");

  const submit = (e) => {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed) return;
    setActiveAddress(trimmed);
  };

  return (
    <form onSubmit={submit} className={compact ? "flex items-center gap-2" : "flex items-center gap-2 flex-wrap"}>
      <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-md px-3 py-2 flex-1 min-w-[220px]">
        <Search className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Enter a candidate address…"
          className="bg-transparent outline-none text-xs text-slate-200 placeholder:text-slate-600 w-full"
        />
      </div>
      <Button type="submit" size="sm" className="bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs">
        Analyze
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="border-slate-700 text-slate-200 text-xs"
        onClick={() => draft.trim() && addToWatchlist(draft.trim())}
      >
        <Plus className="w-3.5 h-3.5 mr-1" /> Save
      </Button>
    </form>
  );
}
