"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useWorkspaceContext } from "@/lib/workspace-context";
import { Briefing, BriefingAudience, BriefingDigestType, ChangeLog } from "@/lib/types";

const STATUS_STYLES: Record<Briefing["status"], string> = {
  draft: "bg-[var(--bg-track)] text-[var(--text-dim)]",
  pending_approval: "bg-[var(--accent-wash)] text-[var(--accent)]",
  approved: "bg-[var(--teal)]/15 text-[var(--teal)]",
  rejected: "bg-[var(--red)]/15 text-[var(--red)]",
  delivered: "bg-[var(--blue)]/15 text-[var(--blue)]",
};

export default function BriefingsPage() {
  const { workspaceId, ready: contextReady, canEdit } = useWorkspaceContext();

  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [changeLogs, setChangeLogs] = useState<ChangeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [audience, setAudience] = useState<BriefingAudience>("all");
  const [digestType, setDigestType] = useState<BriefingDigestType>("urgent");
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async (wsId: number) => {
    try {
      const [briefingList, logs] = await Promise.all([
        apiFetch(`/workspaces/${wsId}/briefings/`),
        apiFetch(`/workspaces/${wsId}/change-logs/`),
      ]);
      setBriefings(briefingList);
      setChangeLogs(logs);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    void (async () => {
      await load(workspaceId);
    })();
  }, [workspaceId, load]);

  function toggleSelected(id: number) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    if (!workspaceId || selectedIds.length === 0) return;

    setGenerating(true);
    setError(null);
    try {
      await apiFetch(`/workspaces/${workspaceId}/briefings/generate-now`, {
        method: "POST",
        body: JSON.stringify({
          audience,
          digest_type: digestType,
          change_log_ids: selectedIds,
        }),
      });
      setSelectedIds([]);
      await load(workspaceId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate briefing");
    } finally {
      setGenerating(false);
    }
  }

  if (!contextReady || loading) return null;

  return (
    <div className="flex flex-col gap-[18px] px-[34px] py-[30px] pb-[44px]" style={{ maxWidth: 860 }}>
      <div className="flex flex-col gap-[7px]">
        <h1 className="m-0 text-[26px] font-semibold tracking-[-0.025em]">Briefings</h1>
        <p className="m-0 max-w-[560px] text-[13.5px] text-[var(--text-muted)]">
          Digest drafts assembled from detected changes, held for approval before anything reaches
          Slack, email, or a CRM.
        </p>
      </div>

      {error && (
        <p className="rounded-lg bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>
      )}

      {canEdit && (
        <div className="flex flex-col gap-4 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5">
          <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">
            Generate a briefing
          </h2>
          <form onSubmit={handleGenerate} className="flex flex-col gap-4">
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex flex-1 flex-col gap-1.5">
                <label className="text-xs font-medium text-[var(--text-muted)]">Audience</label>
                <select
                  value={audience}
                  onChange={(e) => setAudience(e.target.value as BriefingAudience)}
                  className="w-full rounded-lg border border-[var(--border-input)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-secondary)]"
                >
                  <option value="all">All</option>
                  <option value="exec">Exec</option>
                  <option value="sales">Sales</option>
                  <option value="product">Product</option>
                </select>
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <label className="text-xs font-medium text-[var(--text-muted)]">Digest type</label>
                <select
                  value={digestType}
                  onChange={(e) => setDigestType(e.target.value as BriefingDigestType)}
                  className="w-full rounded-lg border border-[var(--border-input)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-secondary)]"
                >
                  <option value="urgent">Urgent</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[var(--text-muted)]">Source changes</label>
              {changeLogs.length === 0 ? (
                <p className="text-sm text-[var(--text-faint)]">
                  No detected changes yet to draft a briefing from.
                </p>
              ) : (
                <ul className="flex max-h-56 flex-col gap-1 overflow-y-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-nested)] p-2">
                  {changeLogs.map((log) => (
                    <li key={log.id}>
                      <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(log.id)}
                          onChange={() => toggleSelected(log.id)}
                          className="accent-[var(--accent)]"
                        />
                        <span className="rounded-md bg-[var(--bg-track)] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
                          {log.classification ?? "unscored"}
                        </span>
                        <span className="truncate">{log.rationale ?? log.diff ?? `#${log.id}`}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <button
              type="submit"
              disabled={generating || selectedIds.length === 0}
              className="h-8 w-fit rounded-lg bg-[var(--accent)] px-3 text-xs font-semibold text-[var(--accent-on)] disabled:opacity-50"
            >
              {generating ? "Generating..." : "Generate briefing"}
            </button>
          </form>
        </div>
      )}

      <div className="flex flex-col gap-[14px]">
        <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">All briefings</h2>
        {briefings.length === 0 ? (
          <p className="text-sm text-[var(--text-faint)]">No briefings yet.</p>
        ) : (
          <div className="flex flex-col gap-[14px]">
            {briefings.map((b) => (
              <div
                key={b.id}
                className="flex flex-col gap-3 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[14.5px] font-semibold tracking-tight">{b.title}</span>
                  <span
                    className={`rounded-md px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide ${STATUS_STYLES[b.status]}`}
                  >
                    {b.status.replace("_", " ")}
                  </span>
                </div>
                <p className="font-mono text-[11px] text-[var(--text-faint)]">
                  {b.audience} &middot; {b.digest_type} &middot;{" "}
                  {new Date(b.created_at).toLocaleString()}
                </p>
                <p className="whitespace-pre-wrap text-[13px] leading-[1.6] text-[var(--text-secondary)]">
                  {b.body_markdown}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
