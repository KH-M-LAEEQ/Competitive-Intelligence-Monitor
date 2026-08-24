export function materialityStyle(score: number): { color: string; label: string } {
  if (score >= 90) return { color: "#FF6B81", label: "critical" };
  if (score >= 80) return { color: "#FF6B81", label: "high" };
  if (score >= 50) return { color: "#FFB020", label: "moderate" };
  return { color: "#35D6A4", label: "low" };
}

export default function MaterialityBar({ score }: { score: number }) {
  const { color, label } = materialityStyle(score);

  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
        Materiality
      </span>
      <div className="flex items-baseline gap-1.5">
        <span className="text-[22px] font-semibold tracking-tight" style={{ color }}>
          {(score / 100).toFixed(2)}
        </span>
        <span className="text-[11px] text-[var(--text-muted)]">{label}</span>
      </div>
      <div className="h-[5px] overflow-hidden rounded-full bg-[var(--bg-track)]">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  );
}
