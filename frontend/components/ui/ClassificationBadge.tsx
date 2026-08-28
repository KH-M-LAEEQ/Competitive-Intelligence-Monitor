const STYLES: Record<string, { bg: string; color: string; label: string }> = {
  pricing_move: { bg: "#F5A5241A", color: "#F5A524", label: "PRICING MOVE" },
  new_feature: { bg: "#4D9FFF1A", color: "#4D9FFF", label: "NEW FEATURE" },
  positioning_shift: { bg: "#9B7BFF1A", color: "#9B7BFF", label: "POSITIONING" },
  hiring_signal: { bg: "#20C9971A", color: "#20C997", label: "HIRING" },
  promotion: { bg: "#F0445E1A", color: "#F0445E", label: "PROMOTION" },
  other: { bg: "#8B98A81A", color: "#8B98A8", label: "OTHER" },
};

export function classificationColor(classification: string | null): string {
  if (!classification) return "var(--text-dim)";
  return (STYLES[classification] ?? STYLES.other).color;
}

export default function ClassificationBadge({
  classification,
}: {
  classification: string | null;
}) {
  if (!classification) {
    return (
      <span className="rounded-md px-2 py-0.5 font-mono text-[10px] tracking-wide text-[var(--text-dim)]">
        UNSCORED
      </span>
    );
  }

  const style = STYLES[classification] ?? STYLES.other;

  return (
    <span
      className="rounded-md px-2 py-0.5 font-mono text-[10px] tracking-wide"
      style={{ background: style.bg, color: style.color }}
    >
      {style.label}
    </span>
  );
}
