import { useCallback, useEffect, useRef, useState } from "react";

import { checkHealth } from "../lib/api";

export type HealthStatus = "checking" | "online" | "offline";

interface UseHealthResult {
  status: HealthStatus;
  lastChecked: Date | null;
  refresh: () => Promise<void>;
}

export function useHealth(intervalMs = 30_000): UseHealthResult {
  const [status, setStatus] = useState<HealthStatus>("checking");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    setStatus((previous) => (previous === "online" ? "online" : "checking"));

    try {
      const online = await checkHealth();
      setStatus(online ? "online" : "offline");
    } catch {
      setStatus("offline");
    } finally {
      inFlight.current = false;
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      void refresh();
    }, intervalMs);

    return () => window.clearInterval(interval);
  }, [intervalMs, refresh]);

  return { status, lastChecked, refresh };
}
