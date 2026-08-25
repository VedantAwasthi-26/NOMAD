import {
  LayoutGrid,
  Building2,
  Network,
  ShieldAlert,
  Database,
  Settings as SettingsIcon,
} from "lucide-react";

export const NAV = [
  { id: "overview", label: "Overview", icon: LayoutGrid, path: "/" },
  { id: "feasibility", label: "Site Feasibility", icon: Building2, path: "/feasibility" },
  { id: "network", label: "Network Monitor", icon: Network, path: "/network" },
  { id: "risk", label: "Risk & Regulatory", icon: ShieldAlert, path: "/risk" },
  { id: "data-sources", label: "Data Sources", icon: Database, path: "/data-sources" },
  { id: "settings", label: "Settings", icon: SettingsIcon, path: "/settings" },
];

export const PAGE_TITLE = {
  overview: "Operations Decision Intelligence",
  feasibility: "Site Feasibility v2.1",
  network: "Network Monitor",
  risk: "Risk & Regulatory",
  "data-sources": "Data Sources",
  settings: "System Settings",
};
