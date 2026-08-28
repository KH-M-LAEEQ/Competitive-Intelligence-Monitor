"use client";

import { createContext, useContext, useCallback, useRef, useState, ReactNode } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useWorkspaceContext } from "@/lib/workspace-context";
import { useToast } from "@/components/ui/Toast";
import { BriefingAudience, BriefingDigestType, BriefingJob } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

interface StartBriefingJobPayload {
  audience?: BriefingAudience;
  digest_type?: BriefingDigestType;
  change_log_ids: number[];
}

interface BriefingJobsContextValue {
  startBriefingJob: (payload: StartBriefingJobPayload) => Promise<boolean>;
  activeJobCount: number;
  // Bumps by one every time any job resolves (success or failure) — pages
  // that list briefings can watch this in a useEffect to refetch without
  // each one needing its own polling loop.
  completedCount: number;
}

const BriefingJobsContext = createContext<BriefingJobsContextValue | null>(null);

export function useBriefingJobs(): BriefingJobsContextValue {
  const ctx = useContext(BriefingJobsContext);
  if (!ctx) {
    throw new Error("useBriefingJobs must be used within BriefingJobsProvider");
  }
  return ctx;
}

export function BriefingJobsProvider({ children }: { children: ReactNode }) {
  const { workspaceId } = useWorkspaceContext();
  const { push } = useToast();
  // Tracks setInterval handles per job id so polling survives client-side
  // navigation (this provider is mounted above the page shell) and gets
  // cleared exactly once when a job resolves.
  const pollersRef = useRef<Record<number, ReturnType<typeof setInterval>>>({});
  const [activeJobCount, setActiveJobCount] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);

  const pollJob = useCallback(
    (wsId: number, jobId: number) => {
      setActiveJobCount((n) => n + 1);

      const resolve = () => {
        clearInterval(pollersRef.current[jobId]);
        delete pollersRef.current[jobId];
        setActiveJobCount((n) => Math.max(0, n - 1));
        setCompletedCount((n) => n + 1);
      };

      const interval = setInterval(async () => {
        try {
          const job: BriefingJob = await apiFetch(
            `/workspaces/${wsId}/briefings/jobs/${jobId}`
          );
          if (job.status === "success") {
            resolve();
            push({
              tone: "success",
              message: "Briefing ready — sent to approval queue",
              href: "/approvals",
            });
          } else if (job.status === "failed") {
            resolve();
            push({
              tone: "error",
              message: job.error || "Briefing generation failed",
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

  const startBriefingJob = useCallback(
    async (payload: StartBriefingJobPayload): Promise<boolean> => {
      if (!workspaceId) return false;
      try {
        const job: BriefingJob = await apiFetch(
          `/workspaces/${workspaceId}/briefings/generate-now`,
          { method: "POST", body: JSON.stringify(payload) }
        );
        pollJob(workspaceId, job.id);
        return true;
      } catch (err) {
        push({
          tone: "error",
          message: err instanceof ApiError ? err.message : "Failed to start briefing generation",
        });
        return false;
      }
    },
    [workspaceId, pollJob, push]
  );

  return (
    <BriefingJobsContext.Provider value={{ startBriefingJob, activeJobCount, completedCount }}>
      {children}
    </BriefingJobsContext.Provider>
  );
}
