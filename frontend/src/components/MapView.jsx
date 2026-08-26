import { useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

/**
 * Live map. Feed it real coordinates from the backend and it just
 * works — no API key required (uses OpenStreetMap tiles).
 *
 * sites: [{ id, name, lat, lng, score?, tone? }]
 *   tone: "teal" | "amber" | "red" | "slate" — controls marker color
 */
const TONE_COLORS = {
  teal: "#2dd4bf",
  amber: "#fbbf24",
  red: "#f87171",
  slate: "#94a3b8",
};

function FitBounds({ sites }) {
  const map = useMap();
  useMemo(() => {
    if (!sites || sites.length === 0) return;
    if (sites.length === 1) {
      map.setView([sites[0].lat, sites[0].lng], 11);
      return;
    }
    const bounds = sites.map((s) => [s.lat, s.lng]);
    map.fitBounds(bounds, { padding: [30, 30] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sites]);
  return null;
}

export default function MapView({ sites = [], height = "13rem", onSiteClick }) {
  const center = sites.length > 0 ? [sites[0].lat, sites[0].lng] : [39.8283, -98.5795];

  return (
    <div style={{ height }} className="relative rounded-lg overflow-hidden border border-slate-800">
      <MapContainer
        center={center}
        zoom={sites.length > 0 ? 11 : 4}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%", background: "#0f172a" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <FitBounds sites={sites} />
        {sites.map((s) => (
          <CircleMarker
            key={s.id ?? s.name}
            center={[s.lat, s.lng]}
            radius={8}
            pathOptions={{
              color: TONE_COLORS[s.tone] || TONE_COLORS.teal,
              fillColor: TONE_COLORS[s.tone] || TONE_COLORS.teal,
              fillOpacity: 0.85,
              weight: 2,
            }}
            eventHandlers={onSiteClick ? { click: () => onSiteClick(s) } : undefined}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              <span className="font-mono text-[11px]">
                {s.name}
                {s.score != null ? ` · score ${s.score}` : ""}
              </span>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
