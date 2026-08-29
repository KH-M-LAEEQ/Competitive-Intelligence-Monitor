"use client";

import { createContext, useContext, useCallback, useRef, useState, ReactNode } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useWorkspaceContext } from "@/lib/workspace-context";
import { useToast } from "@/components/ui/Toast";
import { BattlecardUpdateJob } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

interface StartBattlecardUpdateJobPayload {
  competitorId: number;
  change_log_ids: number[];
}

interface BattlecardJobsContextValue {
  startBattlecardUpdateJob: (payload: StartBattlecardUpdateJobPayload) => Promise<boolean>;
  // Competitor ids with a proposal currently generating — lets the page show
  // a "Generating..." state on the right competitor's card instead of a
  // generic global count.
  activeCompetitorIds: number[];
  // Bumps by one every time any job resolves (success or failure) — pages
  // showing battlecard content can watch this in a useEffect to refetch
  // without each one needing its own polling loop.
  completedCount: number;
}

const BattlecardJobsContext = createContext<BattlecardJobsContextValue | null>(null);

export function useBattlecardJobs(): BattlecardJobsContextValue {
  const ctx = useContext(BattlecardJobsContext);
  if (!ctx) {
    throw new Error("useBattlecardJobs must be used within BattlecardJobsProvider");
  }
  return ctx;
}

export function BattlecardJobsProvider({ children }: { children: ReactNode }) {
  const { workspaceId } = useWorkspaceContext();
  const { push } = useToast();
  // Tracks setInterval handles per job id so polling survives client-side
  // navigation (this provider is mounted above the page shell) and gets
  // cleared exactly once when a job resolves.
  const pollersRef = useRef<Record<number, ReturnType<typeof setInterval>>>({});
  const [activeByJob, setActiveByJob] = useState<Record<number, number>>({});
  const [completedCount, setCompletedCount] = useState(0);

  const pollJob = useCallback(
    (wsId: number, competitorId: number, jobId: number) => {
      setActiveByJob((prev) => ({ ...prev, [jobId]: competitorId }));

      const resolve = () => {
        clearInterval(pollersRef.current[jobId]);
        delete pollersRef.current[jobId];
        setActiveByJob((prev) => {
          const next = { ...prev };
          delete next[jobId];
          return next;
        });
        setCompletedCount((n) => n + 1);
      };

      const interval = setInterval(async () => {
        try {
          const job: BattlecardUpdateJob = await apiFetch(
            `/workspaces/${wsId}/competitors/${competitorId}/battlecard/updates/jobs/${jobId}`
          );
          if (job.status === "success") {
            resolve();
            push({
              tone: "success",
              message: "Battlecard update ready — sent to approval queue",
              href: "/approvals",
            });
          } else if (job.status === "failed") {
            resolve();
            push({
              tone: "error",
              message: job.error || "Battlecard update generation failed",
            });
          }
        } catch {
          // A transient poll failure (network blip) isn't worth surfacing —
          // the next tick will just try again.
        }
      }, POLL_INTERVAL_MS);

      pollersRef.current[jobId] = interval;
    },
    [push]
  );

  const startBattlecardUpdateJob = useCallback(
    async ({ competitorId, change_log_ids }: StartBattlecardUpdateJobPayload): Promise<boolean> => {
      if (!workspaceId) return false;
      try {
        const job: BattlecardUpdateJob = await apiFetch(
          `/workspaces/${workspaceId}/competitors/${competitorId}/battlecard/updates`,
          { method: "POST", body: JSON.stringify({ change_log_ids }) }
        );
        pollJob(workspaceId, competitorId, job.id);
        return true;
      } catch (err) {
        push({
          tone: "error",
          message: err instanceof ApiError ? err.message : "Failed to propose battlecard update",
        });
        return false;
      }
    },
    [workspaceId, pollJob, push]
  );

  const activeCompetitorIds = Array.from(new Set(Object.values(activeByJob)));

  return (
    <BattlecardJobsContext.Provider
      value={{ startBattlecardUpdateJob, activeCompetitorIds, completedCount }}
    >
      {children}
    </BattlecardJobsContext.Provider>
  );
}
