const STYLES: Record<string, { bg: string; color: string; label: string }> = {
  pricing_move: { bg: "#FFB0201A", color: "#FFB020", label: "PRICING MOVE" },
  new_feature: { bg: "#4EA8FF1A", color: "#4EA8FF", label: "NEW FEATURE" },
  positioning_shift: { bg: "#8B7BFF1A", color: "#8B7BFF", label: "POSITIONING" },
  hiring_signal: { bg: "#35D6A41A", color: "#35D6A4", label: "HIRING" },
  promotion: { bg: "#FF6B811A", color: "#FF6B81", label: "PROMOTION" },
  other: { bg: "#8A93A01A", color: "#8A93A0", label: "OTHER" },
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
