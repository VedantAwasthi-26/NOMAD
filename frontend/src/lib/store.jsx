import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * Every page in this app revolves around one or more addresses — the
 * backend is address-in, evidence/recommendation-out. This store holds
 * the shared "what are we looking at" state so a user can set an
 * address once (or build a watchlist) and every page reacts to it,
 * instead of each page hardcoding its own fake location.
 */

const STORAGE_KEY = "nomad.watchlist.v1";
const ACTIVE_KEY = "nomad.active-address.v1";
const HISTORY_KEY = "nomad.history.v1";
const HISTORY_LIMIT = 50;

const AppStateContext = createContext(null);

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function loadActive() {
  try {
    return localStorage.getItem(ACTIVE_KEY) || "";
  } catch {
    return "";
  }
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function AppStateProvider({ children }) {
  const [watchlist, setWatchlist] = useState(loadWatchlist);
  const [activeAddress, setActiveAddressState] = useState(loadActive);
  const [history, setHistory] = useState(loadHistory);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    localStorage.setItem(ACTIVE_KEY, activeAddress || "");
  }, [activeAddress]);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }, [history]);

  const setActiveAddress = useCallback((address) => {
    setActiveAddressState(address);
  }, []);

  const addToWatchlist = useCallback((address, label) => {
    const trimmed = address.trim();
    if (!trimmed) return;
    setWatchlist((prev) => {
      if (prev.some((w) => w.address.toLowerCase() === trimmed.toLowerCase())) return prev;
      return [...prev, { id: `${Date.now()}-${trimmed}`, address: trimmed, label: label || trimmed }];
    });
  }, []);

  const removeFromWatchlist = useCallback((id) => {
    setWatchlist((prev) => prev.filter((w) => w.id !== id));
  }, []);

  // Records a decision the user actually ran against a real endpoint —
  // shown on the History page and used for the Overview "Decisions"
  // list. `entry` is free-form per type (feasibility / logistics /
  // etc.) but should always include a short `summary` string.
  const logDecision = useCallback((entry) => {
    setHistory((prev) => {
      const next = [{ id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, at: new Date().toISOString(), ...entry }, ...prev];
      return next.slice(0, HISTORY_LIMIT);
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  const value = useMemo(
    () => ({
      watchlist,
      activeAddress,
      setActiveAddress,
      addToWatchlist,
      removeFromWatchlist,
      history,
      logDecision,
      clearHistory,
    }),
    [watchlist, activeAddress, setActiveAddress, addToWatchlist, removeFromWatchlist, history, logDecision, clearHistory]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
