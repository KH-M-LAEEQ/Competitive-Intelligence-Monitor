export interface DonutDatum {
  label: string;
  count: number;
  color: string;
}

export default function DonutChart({
  data,
  centerValue,
  centerLabel,
}: {
  data: DonutDatum[];
  centerValue: string | number;
  centerLabel: string;
}) {
  const total = data.reduce((sum, d) => sum + d.count, 0) || 1;
  const radius = 66;
  const circumference = 2 * Math.PI * radius;

  const { segments } = data.reduce<{
    cumulative: number;
    segments: Array<DonutDatum & { length: number; dashoffset: number }>;
  }>(
    (acc, d) => {
      const length = d.count === 0 ? 0 : (d.count / total) * circumference;
      return {
        cumulative: acc.cumulative + length,
        segments: [...acc.segments, { ...d, length, dashoffset: -acc.cumulative }],
      };
    },
    { cumulative: 0, segments: [] }
  );

  return (
    <div className="flex items-center gap-[18px]">
      <div className="relative h-[164px] w-[164px] flex-shrink-0">
        <svg width="164" height="164" viewBox="0 0 164 164">
          <circle cx="82" cy="82" r={radius} fill="none" stroke="var(--bg-track)" strokeWidth="22" />
          <g transform="rotate(-90 82 82)" fill="none" strokeWidth="22">
            {segments.map((d) => {
              if (d.count === 0) return null;
              const { length, dashoffset } = d;
              return (
                <circle
                  key={d.label}
                  cx="82"
                  cy="82"
                  r={radius}
                  stroke={d.color}
                  strokeDasharray={`${length} ${circumference - length}`}
                  strokeDashoffset={dashoffset}
                />
              );
            })}
          </g>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5">
          <span className="text-2xl font-semibold tracking-tight">{centerValue}</span>
          <span className="font-mono text-[9px] uppercase tracking-[.12em] text-[var(--text-dim)]">
            {centerLabel}
          </span>
        </div>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-[11px]">
        {data.length === 0 ? (
          <p className="text-xs text-[var(--text-faint)]">No data yet.</p>
        ) : (
          data.map((d) => (
            <div key={d.label} className="flex items-center gap-[9px]">
              <span
                className="h-2 w-2 flex-shrink-0 rounded-sm"
                style={{ background: d.color }}
              />
              <span className="flex-1 truncate text-[12.5px] text-[var(--text-secondary)]">
                {d.label}
              </span>
              <span className="font-mono text-xs font-medium text-[var(--text-primary)]">
                {Math.round((d.count / total) * 100)}%
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
