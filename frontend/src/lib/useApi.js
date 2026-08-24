import { useEffect, useRef, useState } from "react";

/**
 * Runs an async call (typically one of the functions in `api.js`) and
 * tracks loading/error/data state. Re-runs whenever `deps` changes —
 * pass the address (and any other params the call depends on) as deps
 * so the page refetches when the user changes what they're looking at.
 *
 * Pass `enabled: false` to skip fetching (e.g. no address entered yet).
 */
export function useAsync(apiCall, deps = [], { enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const run = () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    apiCall(controller.signal)
      .then((result) => setData(result))
      .catch((err) => {
        if (err.name !== "AbortError") setError(err);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    run();
    return () => controllerRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, refetch: run };
}

// Back-compat alias — some pages/components may still import `useApi`.
export const useApi = useAsync;
