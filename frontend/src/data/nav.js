import {
  LayoutGrid,
  Building2,
  Network,
  ShieldAlert,
  Database,
  Settings as SettingsIcon,
  Columns3,
  Route as RouteIcon,
  Clock,
  PlusCircle,
} from "lucide-react";

export const NAV = [
  { id: "overview", label: "Overview", icon: LayoutGrid, path: "/" },
  { id: "new-decision", label: "New Decision", icon: PlusCircle, path: "/new" },
  { id: "feasibility", label: "Site Feasibility", icon: Building2, path: "/feasibility" },
  { id: "compare", label: "Compare", icon: Columns3, path: "/compare" },
  { id: "logistics", label: "Reverse Logistics", icon: RouteIcon, path: "/logistics" },
  { id: "network", label: "Network Monitor", icon: Network, path: "/network" },
  { id: "risk", label: "Risk & Regulatory", icon: ShieldAlert, path: "/risk" },
  { id: "data-sources", label: "Data Sources", icon: Database, path: "/data-sources" },
  { id: "history", label: "History", icon: Clock, path: "/history" },
  { id: "settings", label: "Settings", icon: SettingsIcon, path: "/settings" },
];

export const PAGE_TITLE = {
  overview: "Operations Decision Intelligence",
  "new-decision": "New Decision",
  feasibility: "Site Feasibility v2.1",
  compare: "Location Comparison",
  logistics: "Reverse Logistics",
  network: "Network Monitor",
  risk: "Risk & Regulatory",
  "data-sources": "Data Sources",
  history: "History",
  settings: "System Settings",
};
