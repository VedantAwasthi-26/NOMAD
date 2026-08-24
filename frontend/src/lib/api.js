/**
 * Central API client.
 *
 * This talks to the REAL NOMAD backend contract (FastAPI, see
 * ../../API.md for the full reference), not a hypothetical REST API.
 * Every endpoint here is address-driven and POST-based, matching
 * app/api/routes/*.py in the backend repo:
 *
 *   - Vedant's "raw" endpoints return a Mireye-derived bucket of fields
 *     (FeasibilityResult, SiteSelectionData, RiskData, ...). Nothing is
 *     scored or explained — it's evidence.
 *   - The /decision/* endpoints (AI decision engine, additive on top of
 *     the same backend) return a `Recommendation`: a scored, explained,
 *     gap-flagged verdict. That's the contract the UI should prefer
 *     wherever a verdict/score/explanation is shown.
 *
 * The backend and AI decision-engine folders aren't merged into this
 * repo yet (other contributors are adding them), so until
 * VITE_API_BASE_URL points at a running instance, USE_MOCK keeps the
 * app fully working with mock objects shaped exactly like the real
 * Pydantic response models below.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const USE_MOCK = import.meta.env.VITE_USE_MOCK_DATA === "true";

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, { method = "POST", body, signal } = {}) {
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(
      `Couldn't reach the backend at ${BASE_URL}${path}. Is it running?`,
      0,
      null
    );
  }

  if (!res.ok) {
    let errBody = null;
    try {
      errBody = await res.json();
    } catch {
      /* non-JSON error body, ignore */
    }
    const detail = errBody?.detail ? ` — ${JSON.stringify(errBody.detail)}` : "";
    throw new ApiError(
      `${method} ${path} failed with ${res.status}${detail}`,
      res.status,
      errBody
    );
  }

  if (res.status === 204) return null;
  return res.json();
}

function mockDelay(value, ms = 350) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

// ---------------------------------------------------------------------
// Backend health
// ---------------------------------------------------------------------

async function health(signal) {
  if (USE_MOCK) return mockDelay({ status: "mock" }, 150);
  return request("/locations/health", { method: "GET", signal });
}

// ---------------------------------------------------------------------
// Vedant's raw endpoints — one Mireye-derived bucket per module.
// All take an address (and occasionally extra params) and return the
// evidence shapes defined in app/integrations/mireye/*.py.
// ---------------------------------------------------------------------

async function getVerification(address, signal) {
  if (USE_MOCK) return mockDelay(mock.verification(address));
  return request("/verification/", { body: { address }, signal });
}

async function getFeasibility(address, signal) {
  if (USE_MOCK) return mockDelay(mock.feasibility(address));
  return request("/feasibility/", { body: { address }, signal });
}

async function getSiteSelection(address, signal) {
  if (USE_MOCK) return mockDelay(mock.siteSelection(address));
  return request("/site-selection/", { body: { address }, signal });
}

async function getRisk(address, signal) {
  if (USE_MOCK) return mockDelay(mock.risk(address));
  return request("/risk/", { body: { address }, signal });
}

async function getRegulatory(address, signal) {
  if (USE_MOCK) return mockDelay(mock.regulatory(address));
  return request("/regulatory/", { body: { address }, signal });
}

async function getCatchment(address, radiusKm, signal) {
  if (USE_MOCK) return mockDelay(mock.catchment(address, radiusKm));
  return request("/catchment/", { body: { address, radius_km: radiusKm }, signal });
}

async function getPermitResearch(address, businessType, intendedUse, signal) {
  if (USE_MOCK) return mockDelay(mock.permitResearch(address, businessType, intendedUse));
  return request("/permit-research/", {
    body: { address, business_type: businessType, intended_use: intendedUse },
    signal,
  });
}

async function getMultiLocation(addresses, signal) {
  if (USE_MOCK) return mockDelay(mock.multiLocation(addresses));
  return request("/multi-location/", { body: { addresses }, signal });
}

async function getReverseLogistics(originAddress, destinationAddresses, signal) {
  if (USE_MOCK) return mockDelay(mock.reverseLogistics(originAddress, destinationAddresses));
  return request("/reverse-logistics/", {
    body: { origin_address: originAddress, destination_addresses: destinationAddresses },
    signal,
  });
}

async function getInventoryTransfer(sourceAddresses, destinationAddresses, signal) {
  if (USE_MOCK) return mockDelay(mock.inventoryTransfer(sourceAddresses, destinationAddresses));
  return request("/inventory-transfer/", {
    body: { source_addresses: sourceAddresses, destination_addresses: destinationAddresses },
    signal,
  });
}

// Vedant's "/decision-engine/" — a raw location-context bucket. Distinct
// from the AI layer's "/decision/*" endpoints below despite the similar
// name; kept separate to match the backend exactly.
async function getLocationContext(address, signal) {
  if (USE_MOCK) return mockDelay(mock.locationContext(address));
  return request("/decision-engine/", { body: { address }, signal });
}

// ---------------------------------------------------------------------
// AI decision engine — /decision/*. Returns `Recommendation`: scored,
// explained, gap-flagged. Prefer this wherever the UI shows a verdict.
// ---------------------------------------------------------------------

async function decideFeasibility(address, signal) {
  if (USE_MOCK) return mockDelay(mock.recommendation(address, "feasibility"));
  return request("/decision/feasibility", { body: { address }, signal });
}

async function decideSiteSelection(address, signal) {
  if (USE_MOCK) return mockDelay(mock.recommendation(address, "site_selection"));
  return request("/decision/site-selection", { body: { address }, signal });
}

// The flagship multi-agent endpoint (Site Selection + Regulatory + Risk +
// Demand agents fanned out in parallel). Prefer this over
// decideSiteSelection when you want the full agent evidence.
async function decideSiteSelectionAgents(address, signal) {
  if (USE_MOCK) return mockDelay(mock.recommendation(address, "site_selection_agents"));
  return request("/decision/site-selection/agents", { body: { address }, signal });
}

async function decideLogistics(originAddress, destinationAddresses, signal) {
  if (USE_MOCK) return mockDelay(mock.logistics(originAddress, destinationAddresses));
  return request("/decision/logistics", {
    body: { origin_address: originAddress, destination_addresses: destinationAddresses },
    signal,
  });
}

async function decideQuery(query, address, destinationAddresses, signal) {
  if (USE_MOCK) return mockDelay(mock.query(query, address, destinationAddresses));
  return request("/decision/query", {
    body: { query, address, destination_addresses: destinationAddresses },
    signal,
  });
}

export const api = {
  health,
  getVerification,
  getFeasibility,
  getSiteSelection,
  getRisk,
  getRegulatory,
  getCatchment,
  getPermitResearch,
  getMultiLocation,
  getReverseLogistics,
  getInventoryTransfer,
  getLocationContext,
  decideFeasibility,
  decideSiteSelection,
  decideSiteSelectionAgents,
  decideLogistics,
  decideQuery,
};

// ---------------------------------------------------------------------
// Mock data — shaped exactly like the real Pydantic response models,
// so nothing in the pages needs to change when USE_MOCK flips off.
// Deterministic-ish per address so re-running with the same input
// doesn't visibly jitter the UI.
// ---------------------------------------------------------------------

function seededScore(address, base, spread) {
  let h = 0;
  for (let i = 0; i < address.length; i++) h = (h * 31 + address.charCodeAt(i)) >>> 0;
  return Math.round(base + (h % 1000) / 1000 * spread);
}

function fakeLatLng(address) {
  let h = 0;
  for (let i = 0; i < address.length; i++) h = (h * 33 + address.charCodeAt(i)) >>> 0;
  const lat = 25 + (h % 2000) / 100; // ~25-45
  const lng = -122 + ((h >> 3) % 4500) / 100; // ~-122 to -77
  return { lat: Number(lat.toFixed(4)), lng: Number(lng.toFixed(4)) };
}

const mock = {
  verification(address) {
    const { lat, lng } = fakeLatLng(address);
    return {
      lat,
      lng,
      fetched_at: new Date().toISOString(),
      fields: {
        formatted_address: address,
        parcel_id: "MOCK-PARCEL-0001",
        zoning_code: "M-2",
      },
      partial_failures: [],
    };
  },
  feasibility(address) {
    const { lat, lng } = fakeLatLng(address);
    const score = seededScore(address, 55, 35);
    return {
      lat,
      lng,
      feasible: score >= 60,
      score,
      factors: {
        nearest_major_road_distance_m: 420,
        county_population: 812000,
        flood_zone: "X",
        zoning_permitted_use: true,
      },
      blockers: score < 60 ? ["flagged: below feasibility threshold (mock)"] : [],
      data_quality: [
        { field: "nearest_major_road_distance_m", status: "ok", source: "mireye" },
        { field: "flood_zone", status: "ok", source: "mireye" },
      ],
    };
  },
  siteSelection(address) {
    const { lat, lng } = fakeLatLng(address);
    return {
      lat,
      lng,
      physical: { nearest_major_road_distance_m: 420, parcel_area_sqm: 18500 },
      geographic: { elevation_m: 112, terrain: "flat" },
      regulatory: { zoning_permitted_use: true },
      demographic: { county_population: 812000, median_household_income: 68500 },
      data_quality: [{ field: "parcel_area_sqm", status: "ok", source: "mireye" }],
    };
  },
  risk(address) {
    const { lat, lng } = fakeLatLng(address);
    return {
      lat,
      lng,
      facility_risks: { fire_risk_index: 24, structural_risk_index: 12 },
      route_risks: { primary_route_congestion_index: 41 },
      environmental_risks: {
        flood_exposure_index: seededScore(address, 15, 50),
        wildfire_exposure_index: seededScore(address + "w", 15, 50),
        wind_storm_exposure_index: seededScore(address + "s", 15, 50),
      },
      data_quality: [{ field: "flood_exposure_index", status: "ok", source: "external_disaster" }],
    };
  },
  regulatory(address) {
    const { lat, lng } = fakeLatLng(address);
    return {
      lat,
      lng,
      regulations: { zoning_code: "C-1", permitted_use: true },
      restrictions: { loading_dock_hours: "22:00-06:00 restricted" },
      environmental_constraints: { wetland_overlay: false },
      data_quality: [{ field: "zoning_code", status: "ok", source: "mireye" }],
    };
  },
  catchment(address, radiusKm) {
    const { lat, lng } = fakeLatLng(address);
    return {
      address,
      lat,
      lng,
      radius_km: radiusKm,
      population: { total: 812000, within_radius: 214000 },
      proximity: { nearest_competitor_km: 4.2 },
      demand_estimate: { monthly_units: 18400 },
      market_potential: { index: seededScore(address, 50, 40) },
      data_quality: [{ field: "population.total", status: "ok", source: "mireye" }],
    };
  },
  permitResearch(address, businessType, intendedUse) {
    const { lat, lng } = fakeLatLng(address);
    return {
      lat,
      lng,
      zoning: { code: "M-2", permitted: true, business_type: businessType },
      permits: {
        occupancy_permit: "required",
        fire_safety_inspection: "required",
        signage_variance: intendedUse === "retail" ? "required" : "not required",
      },
      restrictions: { hours_of_operation: "06:00-22:00" },
      application_guidance: { estimated_days: 45, agency: "City Planning Dept." },
      data_quality: [{ field: "zoning.code", status: "ok", source: "mireye" }],
    };
  },
  multiLocation(addresses) {
    const locations = addresses.map((address) => {
      const { lat, lng } = fakeLatLng(address);
      return {
        address,
        lat,
        lng,
        fields: { uptime_pct: 95 + seededScore(address, 0, 5), status: "nominal" },
        data_quality: [{ field: "uptime_pct", status: "ok", source: "mireye" }],
      };
    });
    return {
      locations,
      comparative_metrics: { avg_uptime_pct: 97.1 },
      outlier_alerts: [],
      network_insights: { note: "mock — no real comparative signal yet" },
    };
  },
  reverseLogistics(originAddress, destinationAddresses) {
    const origin = fakeLatLng(originAddress);
    return {
      origin_address: originAddress,
      destination_addresses: destinationAddresses,
      origins: [{ address: originAddress, ...origin }],
      destinations: destinationAddresses.map((a) => ({ address: a, ...fakeLatLng(a) })),
      route_factors: { avg_transit_hours: 6.4 },
      destination_ranking: destinationAddresses.map((a, i) => ({
        address: a,
        rank: i + 1,
        score: seededScore(a, 60, 30),
      })),
      data_quality: [],
    };
  },
  inventoryTransfer(sourceAddresses, destinationAddresses) {
    const toLoc = (a) => ({ address: a, ...fakeLatLng(a), fields: {}, data_quality: [] });
    return {
      source_locations: sourceAddresses.map(toLoc),
      destination_locations: destinationAddresses.map(toLoc),
      transfer_factors: { avg_distance_km: 128 },
      transfer_ranking: destinationAddresses.map((a, i) => ({
        address: a,
        rank: i + 1,
        score: seededScore(a, 55, 35),
      })),
      data_quality: [],
    };
  },
  locationContext(address) {
    const { lat, lng } = fakeLatLng(address);
    return {
      address,
      lat,
      lng,
      location_context: { land_use: "industrial", nearest_port_km: 38 },
      data_quality: [{ field: "land_use", status: "ok", source: "mireye" }],
    };
  },
  recommendation(address, mode) {
    const { lat, lng } = fakeLatLng(address);
    const overall = seededScore(address + mode, 50, 40);
    const factors = [
      { factor: "hazard_safety", raw_value: 24, score: 82, weight: 0.25, contribution: 20.5, confidence: 0.9, source_system: "external_disaster", source_fields: ["flood_exposure_index"], note: null },
      { factor: "accessibility", raw_value: 420, score: 74, weight: 0.25, contribution: 18.5, confidence: 0.95, source_system: "mireye", source_fields: ["nearest_major_road_distance_m"], note: null },
      { factor: "regulatory_fit", raw_value: true, score: 90, weight: 0.2, contribution: 18, confidence: 0.8, source_system: "mireye", source_fields: ["zoning_permitted_use"], note: null },
      { factor: "demand", raw_value: 812000, score: 65, weight: 0.3, contribution: 19.5, confidence: 0.7, source_system: "mireye", source_fields: ["county_population"], note: "mock — demand agent not connected yet" },
    ];
    return {
      address,
      lat,
      lng,
      feasible: overall >= 60,
      overall_score: overall,
      confidence: 0.82,
      factor_breakdown: factors,
      strengths: overall >= 60 ? ["Strong road accessibility", "Zoning permits intended use"] : [],
      flagged_gaps:
        overall < 60
          ? [{ field: "demand_estimate", reason: "mock data — Demand agent not wired up", source_system: "derived" }]
          : [],
      hard_floor_triggered: false,
      requires_human_review: overall < 50,
      explanation: `(mock) This is a placeholder explanation for ${mode.replace(/_/g, " ")} — replace with the real /decision/${mode.replace(/_/g, "-")} response once the backend is live.`,
      verified_groundedness: !USE_MOCK,
      mireye_field_count: 6,
      mireye_coverage_note: "mock coverage note",
    };
  },
  logistics(originAddress, destinationAddresses) {
    return {
      origin_address: originAddress,
      ranking: destinationAddresses.map((a, i) => ({
        address: a,
        rank: i + 1,
        overall_score: seededScore(a, 55, 35),
        factors: [
          { factor: "accessibility", score: seededScore(a + "a", 50, 40), weight: 0.4, contribution: 20, confidence: 0.9, source_system: "mireye", source_fields: [] },
          { factor: "infrastructure", score: seededScore(a + "i", 50, 40), weight: 0.3, contribution: 15, confidence: 0.85, source_system: "mireye", source_fields: [] },
          { factor: "hazard_safety", score: seededScore(a + "h", 50, 40), weight: 0.3, contribution: 15, confidence: 0.9, source_system: "external_disaster", source_fields: [] },
        ],
      })),
    };
  },
  query(query, address) {
    return {
      routed_to: "site_selection_agent",
      query,
      address: address || null,
      evidence: { note: "mock — supervisor routing not connected yet" },
    };
  },
};
