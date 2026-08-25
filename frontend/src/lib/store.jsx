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

export function AppStateProvider({ children }) {
  const [watchlist, setWatchlist] = useState(loadWatchlist);
  const [activeAddress, setActiveAddressState] = useState(loadActive);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    localStorage.setItem(ACTIVE_KEY, activeAddress || "");
  }, [activeAddress]);

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

  const value = useMemo(
    () => ({
      watchlist,
      activeAddress,
      setActiveAddress,
      addToWatchlist,
      removeFromWatchlist,
    }),
    [watchlist, activeAddress, setActiveAddress, addToWatchlist, removeFromWatchlist]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
