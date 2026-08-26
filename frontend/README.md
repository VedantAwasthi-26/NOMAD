# Mireye Platform

A React + Vite + Tailwind + shadcn/ui dashboard with sidebar navigation
(Overview, Site Feasibility, Network Monitor, Risk & Regulatory, Data
Sources, Settings), routed with react-router-dom.

## Setup

```bash
npm install
cp .env.example .env
npm run dev       # start local dev server (http://localhost:5173)
npm run build     # production build -> dist/
npm run preview   # preview the production build
```

## Connecting the backend

By default the app runs on built-in mock data (`VITE_USE_MOCK_DATA=true`
in `.env`). Once your teammate's API is up:

1. Set `VITE_API_BASE_URL` in `.env` to the real API URL
2. Set `VITE_USE_MOCK_DATA=false`
3. That's it — Feasibility and Network pages will start pulling live data,
   including live coordinates on the map, with no code changes needed.

Full endpoint contract (request/response shapes) is in **`API.md`** —
share that file with whoever's building the backend.

## The map

`src/components/MapView.jsx` is a real interactive map (Leaflet +
OpenStreetMap tiles, no API key required). It takes a `sites` prop —
`[{ id, name, lat, lng, score?, tone? }]` — and plots markers, auto-fits
bounds, and shows a tooltip per site. Currently used on the Feasibility
and Network pages; drop it into any other page the same way once you
have coordinates to show.

## Structure

```
src/
  components/
    ui/            # shadcn/ui primitives (button, card, badge, progress)
    Sidebar.jsx     # left navigation
    StatCard.jsx
    StatusPill.jsx
  data/
    nav.js          # nav items + page titles
  pages/
    OverviewPage.jsx
    FeasibilityPage.jsx
    NetworkPage.jsx
    RiskPage.jsx
    DataSourcesPage.jsx
    SettingsPage.jsx
  App.jsx           # layout shell + routes
  main.jsx          # entry point (BrowserRouter)
  index.css         # Tailwind + shadcn CSS variables
```

## Adding more shadcn/ui components

This project already includes the pieces used in the dashboard (button,
card, badge, progress). If you later run the official shadcn CLI
(`npx shadcn@latest add <component>`) it will drop new files straight
into `src/components/ui/` alongside these.
