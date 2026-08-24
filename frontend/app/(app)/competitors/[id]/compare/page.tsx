"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { useWorkspaceContext } from "@/lib/workspace-context";
import { CategoryPriceStats, ChangeLog, ComparisonResponse, Competitor, SiteSummary } from "@/lib/types";
import DonutChart from "@/components/charts/DonutChart";
import DualTrendChart from "@/components/charts/DualTrendChart";
import ClassificationBadge from "@/components/ui/ClassificationBadge";

// Cycled in fixed order across category pills — kept distinct from --accent
// (already owns "current offers," the actionable signal on this card) and
// from --red (reserved for destructive/error states elsewhere in the app).
const CATEGORY_HUES = ["#4EA8FF", "#8B7BFF", "#35D6A4"];

const CLASS_COLORS: Record<string, string> = {
  pricing_move: "#FFB020",
  new_feature: "#4EA8FF",
  positioning_shift: "#8B7BFF",
  hiring_signal: "#35D6A4",
  promotion: "#FF6B81",
  other: "#8A93A0",
};
const CLASS_LABELS: Record<string, string> = {
  pricing_move: "Pricing move",
  new_feature: "New feature",
  positioning_shift: "Positioning",
  hiring_signal: "Hiring signal",
  promotion: "Promotion",
  other: "Other",
};

function classificationDonutData(counts: Record<string, number>) {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({
      label: CLASS_LABELS[label] ?? label,
      count,
      color: CLASS_COLORS[label] ?? CLASS_COLORS.other,
    }));
}

function formatVisits(n: number | null) {
  if (n === null) return "—";
  return n.toLocaleString();
}

function formatPrice(n: number, currency: string | null) {
  const rounded = Math.round(n).toLocaleString();
  return currency ? `${currency} ${rounded}` : rounded;
}

export default function ComparePage() {
  const params = useParams();
  const competitorId = Number(params.id);
  const { workspaceId, ready: contextReady, canEdit } = useWorkspaceContext();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ComparisonResponse | null>(null);
  const [changeLogs, setChangeLogs] = useState<ChangeLog[]>([]);
  const [otherCompetitors, setOtherCompetitors] = useState<Competitor[]>([]);
  const [compareTo, setCompareTo] = useState<string>("");
  const [siteSummary, setSiteSummary] = useState<SiteSummary | null>(null);
  const [refreshingSummary, setRefreshingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [priceCache, setPriceCache] = useState<Record<string, CategoryPriceStats>>({});
  const [priceLoadingFor, setPriceLoadingFor] = useState<string | null>(null);
  const [priceError, setPriceError] = useState<string | null>(null);

  const load = useCallback(async (wsId: number, compareToId?: string) => {
    try {
      const query = compareToId ? `?compare_to=${compareToId}` : "";
      const [res, comps, summary, logs] = await Promise.all([
        apiFetch(`/workspaces/${wsId}/competitors/${competitorId}/comparison${query}`),
        apiFetch(`/workspaces/${wsId}/competitors/`),
        apiFetch(`/workspaces/${wsId}/competitors/${competitorId}/site-summary/`).catch(() => null),
        apiFetch(`/workspaces/${wsId}/change-logs/`),
      ]);
      setData(res);
      setOtherCompetitors(comps.filter((c: Competitor) => c.id !== competitorId));
      setSiteSummary(summary);
      setChangeLogs(
        logs
          .filter((l: ChangeLog) => l.competitor_id === competitorId)
          .sort(
            (a: ChangeLog, b: ChangeLog) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
      );
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [competitorId]);

  useEffect(() => {
    if (!workspaceId) return;
    void (async () => {
      await load(workspaceId);
    })();
  }, [workspaceId, load]);

  async function handleCompareToChange(value: string) {
    setCompareTo(value);
    if (!workspaceId) return;
    setLoading(true);
    await load(workspaceId, value || undefined);
  }

  async function handleRefreshSiteSummary() {
    if (!workspaceId) return;
    setRefreshingSummary(true);
    setSummaryError(null);
    try {
      const result = await apiFetch(
        `/workspaces/${workspaceId}/competitors/${competitorId}/site-summary/refresh`,
        { method: "POST" }
      );
      setSiteSummary(result);
    } catch (err) {
      setSummaryError(err instanceof ApiError ? err.message : "Failed to refresh site summary");
    } finally {
      setRefreshingSummary(false);
    }
  }

  async function handleCategoryClick(category: string) {
    setSelectedCategory(category);
    setPriceError(null);
    if (priceCache[category] || !workspaceId) return;

    setPriceLoadingFor(category);
    try {
      const result = await apiFetch(
        `/workspaces/${workspaceId}/competitors/${competitorId}/category-price/`,
        { method: "POST", body: JSON.stringify({ category }) }
      );
      setPriceCache((prev) => ({ ...prev, [category]: result }));
    } catch (err) {
      setPriceError(err instanceof ApiError ? err.message : "Failed to look up pricing");
    } finally {
      setPriceLoadingFor(null);
    }
  }

  if (!contextReady || loading) return null;

  if (error || !data) {
    return (
      <div className="flex flex-col gap-3 px-[34px] py-[30px]" style={{ maxWidth: 900 }}>
        <p className="text-sm text-[var(--text-faint)]">{error ?? "Competitor not found."}</p>
        <Link href="/" className="text-sm font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]">
          Back to dashboard
        </Link>
      </div>
    );
  }

  const { competitor, profile, battlecard, change_summary, traffic, benchmark } = data;
  const benchmarkIsOwnSite = benchmark?.competitor.is_own_site === true;

  return (
    <div className="flex flex-col gap-[18px] px-[34px] py-[30px] pb-[44px]" style={{ maxWidth: 1100 }}>
      <div className="flex items-end justify-between gap-6">
        <div className="flex flex-col gap-[7px]">
          <h1 className="m-0 text-[26px] font-semibold tracking-[-0.025em]">{competitor.name}</h1>
          <p className="m-0 max-w-[560px] text-[13.5px] text-[var(--text-muted)]">
            Every analysis type this competitor has generated, in one view.
          </p>
        </div>
        <Link
          href={`/competitors/${competitor.id}`}
          className="h-8 rounded-lg border border-[var(--border-input)] bg-[var(--bg-card)] px-3 text-xs font-medium leading-8 text-[var(--text-secondary)] hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]"
        >
          Manage surfaces &amp; profile →
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-[14px] lg:grid-cols-4">
        <StatTile label="Changes detected" value={change_summary.total_changes} />
        <StatTile label="Judged material" value={change_summary.material_count} />
        <StatTile
          label="Avg materiality"
          value={
            change_summary.avg_materiality !== null
              ? (change_summary.avg_materiality / 100).toFixed(2)
              : "—"
          }
        />
        <StatTile
          label="Last change"
          value={
            change_summary.last_change_at
              ? new Date(change_summary.last_change_at).toLocaleDateString()
              : "—"
          }
        />
      </div>

      <Card>
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col gap-[5px]">
            <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">
              What&apos;s on their site
            </h2>
            <p className="m-0 text-[11.5px] text-[var(--text-faint)]">
              {siteSummary?.generated_at
                ? `Generated ${new Date(siteSummary.generated_at).toLocaleString()}`
                : "Read directly from their current page content — no diff needed"}
            </p>
          </div>
          {canEdit && (
            <button
              onClick={handleRefreshSiteSummary}
              disabled={refreshingSummary}
              className="h-8 flex-shrink-0 rounded-lg bg-[var(--accent)] px-3 text-xs font-semibold text-[var(--accent-on)] disabled:opacity-50"
            >
              {refreshingSummary ? "Analyzing..." : siteSummary ? "Refresh" : "Analyze site"}
            </button>
          )}
        </div>
        {summaryError && (
          <p className="m-0 text-[12.5px] text-[var(--red)]">{summaryError}</p>
        )}
        {!siteSummary ? (
          <p className="text-sm text-[var(--text-faint)]">
            No site summary yet — click &quot;Analyze site&quot; to extract categories and
            current offers from their most recently captured page content.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
                Categories
              </span>
              {siteSummary.categories.length === 0 ? (
                <span className="text-[13px] text-[var(--text-faint)]">None detected</span>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {siteSummary.categories.map((category, i) => {
                    const hue = CATEGORY_HUES[i % CATEGORY_HUES.length];
                    const isSelected = selectedCategory === category;
                    return (
                      <button
                        key={category}
                        onClick={() => handleCategoryClick(category)}
                        className="rounded-md px-2 py-0.5 font-mono text-[10.5px] font-medium transition-opacity hover:opacity-75"
                        style={{
                          background: `${hue}1A`,
                          color: hue,
                          outline: isSelected ? `1px solid ${hue}` : "none",
                        }}
                      >
                        {category}
                      </button>
                    );
                  })}
                </div>
              )}
              {selectedCategory && (
                <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-nested)] px-3 py-2.5">
                  {priceLoadingFor === selectedCategory ? (
                    <p className="m-0 text-[12.5px] text-[var(--text-faint)]">
                      Looking up pricing for &quot;{selectedCategory}&quot;…
                    </p>
                  ) : priceError ? (
                    <p className="m-0 text-[12.5px] text-[var(--red)]">{priceError}</p>
                  ) : priceCache[selectedCategory] ? (
                    priceCache[selectedCategory].prices_found === 0 ? (
                      <p className="m-0 text-[12.5px] text-[var(--text-faint)]">
                        No pricing found for &quot;{selectedCategory}&quot; — couldn&apos;t locate
                        or read a listing page for this category.
                      </p>
                    ) : (
                      <div className="flex flex-col gap-1">
                        <span className="text-[13px] font-medium text-[var(--text-primary)]">
                          {selectedCategory}:{" "}
                          {formatPrice(
                            priceCache[selectedCategory].min_price!,
                            priceCache[selectedCategory].currency
                          )}{" "}
                          –{" "}
                          {formatPrice(
                            priceCache[selectedCategory].max_price!,
                            priceCache[selectedCategory].currency
                          )}{" "}
                          <span className="text-[var(--text-faint)]">
                            (avg{" "}
                            {formatPrice(
                              priceCache[selectedCategory].avg_price!,
                              priceCache[selectedCategory].currency
                            )}
                            )
                          </span>
                        </span>
                        <span className="text-[11px] text-[var(--text-faint)]">
                          Based on {priceCache[selectedCategory].prices_found} product
                          {priceCache[selectedCategory].prices_found === 1 ? "" : "s"} visible on
                          their listing page
                          {priceCache[selectedCategory].listing_url && (
                            <>
                              {" · "}
                              <a
                                href={priceCache[selectedCategory].listing_url!}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[var(--accent)] hover:underline"
                              >
                                View listing ↗
                              </a>
                            </>
                          )}
                        </span>
                      </div>
                    )
                  ) : null}
                </div>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
                Current offers
              </span>
              {siteSummary.current_offers.length === 0 ? (
                <span className="text-[13px] text-[var(--text-faint)]">None detected</span>
              ) : (
                <ul className="m-0 flex flex-col gap-1.5 pl-4">
                  {siteSummary.current_offers.map((offer) => (
                    <li key={offer} className="text-[13px] font-medium text-[var(--accent)]">
                      {offer}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-[14px] lg:grid-cols-[1.45fr_1fr]">
        <Card>
          <div className="flex flex-col gap-[5px]">
            <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">
              Detection vs. materiality
            </h2>
            <p className="m-0 text-[11.5px] text-[var(--text-faint)]">Last 30 days</p>
          </div>
          <DualTrendChart data={change_summary.trend} />
        </Card>

        <Card>
          <div className="flex flex-col gap-[5px]">
            <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Classification</h2>
            <p className="m-0 text-[11.5px] text-[var(--text-faint)]">All time</p>
          </div>
          <DonutChart
            data={classificationDonutData(change_summary.classification_counts)}
            centerValue={change_summary.total_changes}
            centerLabel="changes"
          />
        </Card>
      </div>

      <Card>
        <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Recent changes</h2>
        {changeLogs.length === 0 ? (
          <p className="text-sm text-[var(--text-faint)]">No changes detected yet for this competitor.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {changeLogs.slice(0, 10).map((log) => (
              <div
                key={log.id}
                className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-nested)] px-4 py-3.5"
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ClassificationBadge classification={log.classification} />
                    {log.materiality_score !== null && (
                      <span className="font-mono text-[11px] text-[var(--text-muted)]">
                        {(log.materiality_score / 100).toFixed(2)} materiality
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-[11px] text-[var(--text-faint)]">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                {log.rationale && (
                  <p className="m-0 mb-2 text-[13px] leading-[1.55] text-[var(--text-secondary)]">
                    {log.rationale}
                  </p>
                )}
                {log.diff && (
                  <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border border-[var(--border-subtler)] bg-[var(--bg-page)] p-3 font-mono text-[11.5px] text-[var(--text-dim)]">
                    {log.diff}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Traffic trend</h2>
        {!traffic || traffic.length === 0 ? (
          <p className="text-sm text-[var(--text-faint)]">
            Traffic tracking not configured — set a website domain on this competitor&apos;s
            company profile and connect SimilarWeb to see estimated monthly visits here.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {traffic.map((snapshot) => (
              <div key={snapshot.id} className="flex items-center justify-between">
                <span className="font-mono text-[11.5px] text-[var(--text-muted)]">
                  {new Date(snapshot.month).toLocaleDateString(undefined, {
                    month: "short",
                    year: "numeric",
                  })}
                </span>
                <span className="font-mono text-[12.5px] text-[var(--text-secondary)]">
                  {formatVisits(snapshot.visits)} visits
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <div className="flex items-center justify-between gap-4">
          <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">
            {competitor.name}
            {benchmark ? ` vs. ${benchmarkIsOwnSite ? "your website" : benchmark.competitor.name}` : ""}
          </h2>
          {!benchmarkIsOwnSite && (
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[.1em] text-[var(--text-faint)]">
                No website set — compare against
              </span>
              <select
                value={compareTo}
                onChange={(e) => handleCompareToChange(e.target.value)}
                className="h-7 rounded-md border border-[var(--border-input)] bg-[var(--bg-input)] px-2 text-xs text-[var(--text-secondary)]"
              >
                <option value="">Select a competitor…</option>
                {otherCompetitors.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        {!benchmark ? (
          <p className="text-sm text-[var(--text-faint)]">
            Set your website on the dashboard, or pick another competitor above, to see a
            side-by-side comparison.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-[14px] font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dimmer)]">
              <span></span>
              <span className="text-right">{competitor.name}</span>
              <span className="text-right text-[var(--accent)]">
                {benchmarkIsOwnSite ? "Your website" : benchmark.competitor.name}
              </span>
            </div>
            <ComparisonRow
              label="Changes detected"
              left={change_summary.total_changes}
              right={benchmark.change_summary.total_changes}
            />
            <ComparisonRow
              label="Judged material"
              left={change_summary.material_count}
              right={benchmark.change_summary.material_count}
            />
            <ComparisonRow
              label="Avg materiality"
              left={
                change_summary.avg_materiality !== null
                  ? (change_summary.avg_materiality / 100).toFixed(2)
                  : "—"
              }
              right={
                benchmark.change_summary.avg_materiality !== null
                  ? (benchmark.change_summary.avg_materiality / 100).toFixed(2)
                  : "—"
              }
            />
            <ComparisonRow
              label="Last change"
              left={
                change_summary.last_change_at
                  ? new Date(change_summary.last_change_at).toLocaleDateString()
                  : "—"
              }
              right={
                benchmark.change_summary.last_change_at
                  ? new Date(benchmark.change_summary.last_change_at).toLocaleDateString()
                  : "—"
              }
            />
          </>
        )}
      </Card>

      <Card>
        <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Company profile</h2>
        {!profile ? (
          <p className="text-sm text-[var(--text-faint)]">No profile filled in yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            <ProfileField label="Industry" value={profile.industry} />
            <ProfileField label="HQ location" value={profile.hq_location} />
            <ProfileField label="Employee range" value={profile.employee_range} />
            <ProfileField label="Funding stage" value={profile.funding_stage} />
            {profile.key_people && profile.key_people.length > 0 && (
              <div className="col-span-2 flex flex-col gap-1">
                <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
                  Key people
                </span>
                <span className="text-[13px] text-[var(--text-secondary)]">
                  {profile.key_people.map((p) => `${p.name} (${p.title})`).join(", ")}
                </span>
              </div>
            )}
            {profile.notes_markdown && (
              <div className="col-span-2 flex flex-col gap-1">
                <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
                  Notes
                </span>
                <p className="m-0 whitespace-pre-wrap text-[13px] text-[var(--text-secondary)]">
                  {profile.notes_markdown}
                </p>
              </div>
            )}
          </div>
        )}
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <h2 className="m-0 text-[14.5px] font-semibold tracking-[-0.01em]">Battlecard</h2>
          <Link href="/battlecards" className="text-xs font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]">
            Manage →
          </Link>
        </div>
        {!battlecard ? (
          <p className="text-sm text-[var(--text-faint)]">No battlecard yet for this competitor.</p>
        ) : (
          <>
            <p className="m-0 font-mono text-[11px] text-[var(--text-faint)]">
              Version {battlecard.version}
            </p>
            <pre className="max-h-[200px] overflow-y-auto whitespace-pre-wrap text-[13px] leading-[1.6] text-[var(--text-secondary)]">
              {battlecard.content_markdown || "(empty)"}
            </pre>
          </>
        )}
      </Card>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-[16px] rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-[22px] py-5">
      {children}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex flex-col gap-3 rounded-[14px] border border-[var(--border-default)] bg-[var(--bg-card)] px-5 py-[18px]">
      <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-faint)]">
        {label}
      </span>
      <span className="text-[30px] font-semibold tracking-[-0.03em]">{value}</span>
    </div>
  );
}

function ProfileField({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
        {label}
      </span>
      <span className="text-[13px] text-[var(--text-secondary)]">{value ?? "—"}</span>
    </div>
  );
}

function ComparisonRow({
  label,
  left,
  right,
}: {
  label: string;
  left: string | number;
  right: string | number;
}) {
  return (
    <div className="grid grid-cols-3 items-center gap-[14px] border-t border-[var(--border-subtler)] py-2.5">
      <span className="text-[12.5px] text-[var(--text-secondary)]">{label}</span>
      <span className="text-right font-mono text-[13px] font-medium">{left}</span>
      <span className="text-right font-mono text-[13px] font-medium text-[var(--accent)]">{right}</span>
    </div>
  );
}
