"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { useWorkspaceContext } from "@/lib/workspace-context";
import {
  Battlecard,
  ChangeLog,
  CompanyProfile,
  Competitor,
  KeyPerson,
  Snapshot,
  Surface,
  SurfaceType,
} from "@/lib/types";
import { surfaceDisplayName } from "@/lib/surface-name";
import { SURFACE_TYPE_STYLES, HeadingDot, BaselineCard, ChangeCard } from "@/components/changelog/SurfaceChangeCards";

type CheckStatus =
  | { state: "idle" }
  | { state: "checking" }
  | { state: "done"; message: string }
  | { state: "error"; message: string };

const SURFACE_TYPES: SurfaceType[] = ["pricing", "product", "changelog", "blog", "jobs", "other"];

// Cycled by row index (not by surface_type) so the Pages list reads as
// colorful even when most pages are the generic "other" type — e.g. an
// e-commerce competitor's category pages (Sale, Unstitched, Ready to
// Wear, ...) rarely match a known type, so tying color to type alone
// would leave the whole list the same dull grey.
const ROW_COLORS = ["var(--accent)", "var(--blue)", "var(--violet)", "var(--teal)", "var(--red)"];

const inputClass =
  "w-full rounded-lg border border-[var(--border-input)] bg-[var(--bg-input)] px-3 py-2 text-xs text-[var(--text-secondary)]";
const labelClass = "font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]";

export default function CompetitorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const competitorId = Number(params.id);
  const { workspaceId, workspace, ready: contextReady, canEdit } = useWorkspaceContext();

  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [competitor, setCompetitor] = useState<Competitor | null>(null);
  const [surfaces, setSurfaces] = useState<Surface[]>([]);
  const [changeLogs, setChangeLogs] = useState<ChangeLog[]>([]);
  const [baselineSnapshots, setBaselineSnapshots] = useState<Record<number, Snapshot>>({});
  const [battlecard, setBattlecard] = useState<Battlecard | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [checkStatus, setCheckStatus] = useState<Record<number, CheckStatus>>({});
  const [surfaceForm, setSurfaceForm] = useState({
    surface_type: "pricing" as SurfaceType,
    name: "",
    url: "",
    check_frequency: "daily",
  });
  const [discovering, setDiscovering] = useState(false);
  const [discoverMessage, setDiscoverMessage] = useState<string | null>(null);

  const [profileForm, setProfileForm] = useState({
    industry: "",
    hq_location: "",
    employee_range: "",
    funding_stage: "",
    key_people: "",
    notes_markdown: "",
  });
  const [savingProfile, setSavingProfile] = useState(false);

  const load = useCallback(
    async (wsId: number) => {
      try {
        const [comps, surfs, logs] = await Promise.all([
          apiFetch(`/workspaces/${wsId}/competitors/`),
          apiFetch(`/workspaces/${wsId}/competitors/${competitorId}/surfaces/`),
          apiFetch(`/workspaces/${wsId}/change-logs/`),
        ]);
        setCompetitor(comps.find((c: Competitor) => c.id === competitorId) ?? null);
        setSurfaces(surfs);
        const competitorLogs: ChangeLog[] = logs
          .filter((l: ChangeLog) => l.competitor_id === competitorId)
          .sort(
            (a: ChangeLog, b: ChangeLog) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
        setChangeLogs(competitorLogs);

        // A surface that's been checked but has no ChangeLog yet has
        // nothing to diff against on its first check — fall back to its
        // latest snapshot so "nothing to compare" still shows what's
        // currently on the page instead of showing nothing at all.
        const surfaceIdsWithChanges = new Set(competitorLogs.map((l) => l.surface_id));
        const uncheckedSurfaces = surfs.filter(
          (s: Surface) => s.last_checked_at && !surfaceIdsWithChanges.has(s.id)
        );
        const snapshotEntries = await Promise.all(
          uncheckedSurfaces.map(async (s: Surface) => {
            try {
              const snapshot: Snapshot = await apiFetch(
                `/workspaces/${wsId}/competitors/${competitorId}/surfaces/${s.id}/snapshot`
              );
              return [s.id, snapshot] as const;
            } catch {
              return null;
            }
          })
        );
        setBaselineSnapshots(
          Object.fromEntries(snapshotEntries.filter((e): e is [number, Snapshot] => e !== null))
        );

        try {
          const bc = await apiFetch(`/workspaces/${wsId}/competitors/${competitorId}/battlecard/`);
          setBattlecard(bc);
        } catch {
          setBattlecard(null);
        }

        try {
          const p: CompanyProfile = await apiFetch(
            `/workspaces/${wsId}/competitors/${competitorId}/profile/`
          );
          setProfile(p);
          setProfileForm({
            industry: p.industry ?? "",
            hq_location: p.hq_location ?? "",
            employee_range: p.employee_range ?? "",
            funding_stage: p.funding_stage ?? "",
            key_people: (p.key_people ?? []).map((kp) => `${kp.name} (${kp.title})`).join(", "),
            notes_markdown: p.notes_markdown ?? "",
          });
        } catch {
          setProfile(null);
        }
      } catch (err) {
        if (err instanceof ApiError) setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [competitorId]
  );

  useEffect(() => {
    if (!workspaceId) return;
    void (async () => {
      await load(workspaceId);
    })();
  }, [workspaceId, load]);

  function parseKeyPeople(text: string): KeyPerson[] {
    return text
      .split(",")
      .map((chunk) => chunk.trim())
      .filter(Boolean)
      .map((chunk) => {
        const match = chunk.match(/^(.+?)\s*\((.+)\)$/);
        return match ? { name: match[1].trim(), title: match[2].trim() } : { name: chunk, title: "" };
      });
  }

  async function handleSaveProfile(e: FormEvent) {
    e.preventDefault();
    if (!workspaceId) return;

    setSavingProfile(true);
    setError(null);
    try {
      await apiFetch(`/workspaces/${workspaceId}/competitors/${competitorId}/profile/`, {
        method: "PUT",
        body: JSON.stringify({
          industry: profileForm.industry || null,
          hq_location: profileForm.hq_location || null,
          employee_range: profileForm.employee_range || null,
          funding_stage: profileForm.funding_stage || null,
          key_people: profileForm.key_people ? parseKeyPeople(profileForm.key_people) : null,
          notes_markdown: profileForm.notes_markdown || null,
        }),
      });
      await load(workspaceId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save profile");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleDiscoverSurfaces() {
    if (!workspaceId) return;
    setDiscovering(true);
    setDiscoverMessage(null);
    setError(null);
    try {
      const found: Surface[] = await apiFetch(
        `/workspaces/${workspaceId}/competitors/${competitorId}/surfaces/discover`,
        { method: "POST" }
      );
      setDiscoverMessage(
        found.length === 0
          ? "No new pages found."
          : `Found ${found.length} new page${found.length === 1 ? "" : "s"}.`
      );
      await load(workspaceId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to discover pages");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleAddSurface(e: FormEvent) {
    e.preventDefault();
    if (!workspaceId || !surfaceForm.url) return;

    try {
      await apiFetch(`/workspaces/${workspaceId}/competitors/${competitorId}/surfaces/`, {
        method: "POST",
        body: JSON.stringify({ ...surfaceForm, name: surfaceForm.name.trim() || null }),
      });
      setSurfaceForm({ surface_type: "pricing", name: "", url: "", check_frequency: "daily" });
      await load(workspaceId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add surface");
    }
  }

  async function handleDeleteCompetitor() {
    if (!workspaceId || !competitor) return;
    if (
      !window.confirm(
        `Delete ${competitor.name}? This permanently removes its surfaces, change history, battlecard, and site summary. This cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(true);
    setError(null);
    try {
      await apiFetch(`/workspaces/${workspaceId}/competitors/${competitorId}`, {
        method: "DELETE",
      });
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete competitor");
      setDeleting(false);
    }
  }

  async function handleDeleteSurface(surfaceId: number) {
    if (!workspaceId) return;
    try {
      await apiFetch(`/workspaces/${workspaceId}/competitors/${competitorId}/surfaces/${surfaceId}`, {
        method: "DELETE",
      });
      await load(workspaceId);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
    }
  }

  async function handleCheckSurface(surfaceId: number) {
    if (!workspaceId) return;

    setCheckStatus((prev) => ({ ...prev, [surfaceId]: { state: "checking" } }));
    try {
      const result = await apiFetch(
        `/workspaces/${workspaceId}/competitors/${competitorId}/surfaces/${surfaceId}/check`,
        { method: "POST" }
      );
      const messages: Record<string, string> = {
        baseline_captured: "Baseline captured",
        no_change: "No change detected",
        change_detected: "Change detected",
        already_running: "A check is already running",
      };
      setCheckStatus((prev) => ({
        ...prev,
        [surfaceId]: { state: "done", message: messages[result.status] ?? result.status },
      }));
      await load(workspaceId);
    } catch (err) {
      setCheckStatus((prev) => ({
        ...prev,
        [surfaceId]: { state: "error", message: err instanceof ApiError ? err.message : "Check failed" },
      }));
    }
  }

  if (!contextReady || loading) return null;

  if (!competitor) {
    return (
      <div className="flex flex-col gap-3 px-[34px] py-[30px]" style={{ maxWidth: 900 }}>
        <p className="text-sm text-[var(--text-faint)]">Competitor not found.</p>
        <Link href="/" className="text-sm font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-[18px] px-[34px] py-[30px] pb-[44px]" style={{ maxWidth: 900 }}>
      <div className="flex items-end justify-between gap-6">
        <div className="flex flex-col gap-[7px]">
          <h1 className="m-0 text-[26px] font-semibold tracking-[-0.025em]">{competitor.name}</h1>
          {workspace && (
            <p className="m-0 text-[13.5px] text-[var(--text-muted)]">{workspace.name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              onClick={handleDeleteCompetitor}
              disabled={deleting}
              className="h-8 rounded-lg border border-[var(--red)]/40 px-3 text-xs font-medium text-[var(--red)] disabled:opacity-50"
            >
              {deleting ? "Deleting…" : "Delete competitor"}
            </button>
          )}
          <Link
            href="/"
            className="h-8 rounded-lg border border-[var(--border-input)] bg-[var(--bg-card)] px-3 text-xs font-medium leading-8 text-[var(--text-secondary)] hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]"
          >
            Back to dashboard
          </Link>
        </div>
      </div>

      {error && (
        <p className="rounded-lg bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>
      )}

      <div className="flex flex-col gap-4 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5">
        <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Company profile</h2>
        {canEdit ? (
          <form onSubmit={handleSaveProfile} className="flex flex-col gap-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <label className={labelClass}>Industry</label>
                <input
                  value={profileForm.industry}
                  onChange={(e) => setProfileForm((prev) => ({ ...prev, industry: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass}>HQ location</label>
                <input
                  value={profileForm.hq_location}
                  onChange={(e) => setProfileForm((prev) => ({ ...prev, hq_location: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass}>Employee range</label>
                <input
                  value={profileForm.employee_range}
                  onChange={(e) =>
                    setProfileForm((prev) => ({ ...prev, employee_range: e.target.value }))
                  }
                  placeholder="51-200"
                  className={inputClass}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className={labelClass}>Funding stage</label>
                <input
                  value={profileForm.funding_stage}
                  onChange={(e) =>
                    setProfileForm((prev) => ({ ...prev, funding_stage: e.target.value }))
                  }
                  placeholder="Series B"
                  className={inputClass}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className={labelClass}>Key people (Name (Title), ...)</label>
              <input
                value={profileForm.key_people}
                onChange={(e) => setProfileForm((prev) => ({ ...prev, key_people: e.target.value }))}
                placeholder="Jane Doe (CEO), John Smith (CTO)"
                className={inputClass}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className={labelClass}>Notes</label>
              <textarea
                value={profileForm.notes_markdown}
                onChange={(e) =>
                  setProfileForm((prev) => ({ ...prev, notes_markdown: e.target.value }))
                }
                rows={3}
                className={inputClass}
              />
            </div>
            <button
              type="submit"
              disabled={savingProfile}
              className="h-8 w-fit rounded-lg bg-[var(--accent)] px-3 text-xs font-semibold text-[var(--accent-on)] disabled:opacity-50"
            >
              {savingProfile ? "Saving..." : "Save profile"}
            </button>
          </form>
        ) : (
          !profile && <p className="text-sm text-[var(--text-faint)]">No profile yet for this competitor.</p>
        )}
      </div>

      <div className="flex flex-col gap-4 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5">
        <div className="flex items-center justify-between">
          <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Battlecard</h2>
          <Link href="/battlecards" className="text-xs font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]">
            Manage
          </Link>
        </div>
        {battlecard ? (
          <>
            <p className="m-0 font-mono text-[11px] text-[var(--text-faint)]">
              Version {battlecard.version}
            </p>
            <pre className="whitespace-pre-wrap text-[13px] leading-[1.6] text-[var(--text-secondary)]">
              {battlecard.content_markdown || "(empty)"}
            </pre>
          </>
        ) : (
          <p className="text-sm text-[var(--text-faint)]">No battlecard yet for this competitor.</p>
        )}
      </div>

      <div className="flex flex-col gap-4 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="m-0 flex items-center gap-2 text-[14.5px] font-semibold tracking-[-0.01em]">
            <HeadingDot />
            Pages
          </h2>
          {canEdit && surfaces.length > 0 && (
            <div className="flex items-center gap-2">
              {discoverMessage && (
                <span className="text-[11.5px] text-[var(--text-muted)]">{discoverMessage}</span>
              )}
              <button
                onClick={handleDiscoverSurfaces}
                disabled={discovering}
                className="h-7 rounded-md border border-[var(--border-input)] px-2.5 text-[11.5px] font-medium text-[var(--text-secondary)] hover:border-[var(--border-hover)] disabled:opacity-50"
              >
                {discovering ? "Scanning site..." : "Discover more pages"}
              </button>
            </div>
          )}
        </div>
        <p className="m-0 -mt-2 text-[12px] text-[var(--text-faint)]">
          Every page being monitored on their site — named the same way it is in their own nav
          (Sale, Unstitched, Ready to Wear, ...). Click one to open its change log.
        </p>
        {surfaces.length === 0 ? (
          <p className="text-sm text-[var(--text-faint)]">No surfaces yet.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-[var(--border-subtle)]">
            {surfaces.map((s, i) => {
              const status = checkStatus[s.id] ?? { state: "idle" };
              const typeStyle = SURFACE_TYPE_STYLES[s.surface_type];
              const rowColor = ROW_COLORS[i % ROW_COLORS.length];
              return (
                <Link
                  key={s.id}
                  href={`/competitors/${competitorId}/surfaces/${s.id}`}
                  className="flex items-center justify-between gap-3 px-4 py-3 transition-colors"
                  style={{
                    borderLeft: `3px solid ${rowColor}`,
                    borderBottom: i < surfaces.length - 1 ? "1px solid var(--border-subtler)" : undefined,
                    background: `color-mix(in srgb, ${rowColor} 6%, var(--bg-nested))`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = `color-mix(in srgb, ${rowColor} 14%, var(--bg-nested))`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = `color-mix(in srgb, ${rowColor} 6%, var(--bg-nested))`;
                  }}
                >
                  <div className="min-w-0">
                    <p className="m-0 flex items-center gap-2 text-[13px] font-medium">
                      <span
                        className="flex-shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide"
                        style={{
                          background: `color-mix(in srgb, ${typeStyle.color} 18%, transparent)`,
                          color: typeStyle.color,
                        }}
                      >
                        {s.surface_type}
                      </span>
                      <span className="truncate font-semibold" style={{ color: rowColor }}>
                        {surfaceDisplayName(s)}
                      </span>
                      <span className="truncate font-mono text-[11px] text-[var(--text-dim)]">
                        {s.url.replace(/^https?:\/\//, "")}
                      </span>
                    </p>
                    <p className="m-0 mt-1 font-mono text-[11px] text-[var(--text-faint)]">
                      Checked {s.check_frequency}
                      {s.last_checked_at && ` · last checked ${new Date(s.last_checked_at).toLocaleString()}`}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {status.state === "done" && (
                      <span className="text-[11.5px] text-[var(--text-muted)]">{status.message}</span>
                    )}
                    {status.state === "error" && (
                      <span className="text-[11.5px] text-[var(--red)]">{status.message}</span>
                    )}
                    {canEdit && (
                      <div className="flex items-center gap-2" onClick={(e) => e.preventDefault()}>
                        <button
                          onClick={() => handleCheckSurface(s.id)}
                          disabled={status.state === "checking"}
                          className="h-7 rounded-md border border-[var(--border-input)] px-2.5 text-[11.5px] font-medium text-[var(--text-secondary)] hover:border-[var(--border-hover)] disabled:opacity-50"
                        >
                          {status.state === "checking" ? "Checking..." : "Check now"}
                        </button>
                        <button
                          onClick={() => handleDeleteSurface(s.id)}
                          className="h-7 rounded-md border border-[var(--red)]/40 px-2.5 text-[11.5px] font-medium text-[var(--red)]"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                    <span style={{ color: rowColor }}>›</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {canEdit && (
          <form
            onSubmit={handleAddSurface}
            className="flex flex-col gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-nested)] px-4 py-3.5 sm:flex-row sm:items-end"
          >
            <div className="flex flex-col gap-1.5">
              <label className={labelClass}>Type</label>
              <select
                value={surfaceForm.surface_type}
                onChange={(e) =>
                  setSurfaceForm((prev) => ({ ...prev, surface_type: e.target.value as SurfaceType }))
                }
                className={inputClass}
              >
                {SURFACE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className={labelClass}>Name (optional)</label>
              <input
                value={surfaceForm.name}
                onChange={(e) => setSurfaceForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Unstitched"
                className={inputClass}
              />
            </div>
            <div className="flex-1 flex-col gap-1.5">
              <label className={labelClass}>URL</label>
              <input
                required
                value={surfaceForm.url}
                onChange={(e) => setSurfaceForm((prev) => ({ ...prev, url: e.target.value }))}
                placeholder="https://acme.com/pricing"
                className={inputClass}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className={labelClass}>Frequency</label>
              <select
                value={surfaceForm.check_frequency}
                onChange={(e) =>
                  setSurfaceForm((prev) => ({ ...prev, check_frequency: e.target.value }))
                }
                className={inputClass}
              >
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <button
              type="submit"
              className="h-8 w-fit rounded-lg bg-[var(--accent)] px-3 text-xs font-semibold text-[var(--accent-on)]"
            >
              Add surface
            </button>
          </form>
        )}
      </div>

      <div className="flex flex-col gap-4 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5">
        <h2 className="m-0 flex items-center gap-2 text-[14.5px] font-semibold tracking-[-0.01em]">
          <HeadingDot />
          Change log
        </h2>
        {changeLogs.length === 0 && Object.keys(baselineSnapshots).length === 0 ? (
          <p className="text-sm text-[var(--text-faint)]">No changes detected yet for this competitor.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {Object.entries(baselineSnapshots).map(([surfaceId, snapshot]) => (
              <BaselineCard
                key={`baseline-${surfaceId}`}
                snapshot={snapshot}
                surface={surfaces.find((s) => s.id === Number(surfaceId))}
              />
            ))}
            {changeLogs.map((log) => (
              <ChangeCard
                key={log.id}
                log={log}
                surface={surfaces.find((s) => s.id === log.surface_id)}
                competitorName={competitor?.name}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
