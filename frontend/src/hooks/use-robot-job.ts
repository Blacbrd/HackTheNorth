import { useCallback, useEffect, useRef, useState } from "react";
import { robotApi } from "@/services/api";
import type { RobotJob } from "@/types/api";

const IDLE_MS = 6000;
const ACTIVE_MS = 1000;

/**
 * Follow the robot's current job.
 *
 * Polls rather than streams: the API is plain REST and a fetch a second is
 * cheap on a LAN. It speeds up while a job runs and backs off when idle, so a
 * phone left on the Shelves tab is not hammering the server.
 */
export function useRobotJob(enabled = true) {
  const [job, setJob] = useState<RobotJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stopped = useRef(false);

  const load = useCallback(async () => {
    try {
      const next = await robotApi.job();
      if (!stopped.current) {
        setJob(next);
        setError(null);
      }
      return next;
    } catch (cause) {
      if (!stopped.current) {
        setError(cause instanceof Error ? cause.message : "Lost the robot.");
      }
      return null;
    }
  }, []);

  useEffect(() => {
    stopped.current = false;
    if (!enabled) return;
    let cancelled = false;
    const run = async () => {
      const next = await load();
      if (cancelled || stopped.current) return;
      const busy = Boolean(next?.active || next?.failure);
      timer.current = setTimeout(run, busy ? ACTIVE_MS : IDLE_MS);
    };
    void run();
    return () => {
      cancelled = true;
      stopped.current = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [enabled, load]);

  const recall = useCallback(async () => {
    setJob(await robotApi.recall());
  }, []);

  const clear = useCallback(async () => {
    setJob(await robotApi.clear());
  }, []);

  return { job, error, refresh: load, recall, clear };
}
