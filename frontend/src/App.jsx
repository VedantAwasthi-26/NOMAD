import { Routes, Route, useLocation } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import OverviewPage from "@/pages/OverviewPage";
import FeasibilityPage from "@/pages/FeasibilityPage";
import NetworkPage from "@/pages/NetworkPage";
import RiskPage from "@/pages/RiskPage";
import DataSourcesPage from "@/pages/DataSourcesPage";
import SettingsPage from "@/pages/SettingsPage";
import { NAV, PAGE_TITLE } from "@/data/nav";
import { AppStateProvider, useAppState } from "@/lib/store";
import { USE_MOCK } from "@/lib/api";

function currentPageId(pathname) {
  const match = NAV.find((n) => (n.path === "/" ? pathname === "/" : pathname.startsWith(n.path)));
  return match ? match.id : "overview";
}

function TopBar({ pageId }) {
  const { activeAddress } = useAppState();
  return (
    <div className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/90 backdrop-blur px-8 py-4 flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="text-sm font-semibold text-slate-100">{PAGE_TITLE[pageId]}</div>
        {activeAddress && (
          <div className="text-[10px] font-mono text-slate-500 truncate mt-0.5">{activeAddress}</div>
        )}
      </div>
      <div className="text-[10px] font-mono uppercase tracking-wide px-2 py-1 rounded-full border shrink-0 border-slate-700 text-slate-500">
        {USE_MOCK ? "Mock data" : "Live backend"}
      </div>
    </div>
  );
}

function AppShell() {
  const location = useLocation();
  const pageId = currentPageId(location.pathname);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans flex">
      <Sidebar />

      <div className="flex-1 min-w-0">
        <TopBar pageId={pageId} />

        <div className="max-w-5xl px-8 py-8">
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/feasibility" element={<FeasibilityPage />} />
            <Route path="/network" element={<NetworkPage />} />
            <Route path="/risk" element={<RiskPage />} />
            <Route path="/data-sources" element={<DataSourcesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppStateProvider>
      <AppShell />
    </AppStateProvider>
  );
}
