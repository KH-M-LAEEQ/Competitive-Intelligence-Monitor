import { Surface } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  pricing: "Pricing",
  product: "Product",
  changelog: "Changelog",
  blog: "Blog",
  jobs: "Jobs",
  other: "Page",
};

// Turns "/collections/ready-to-wear" into "Ready To Wear" — used when a
// surface has no name of its own (created before names were tracked, or
// added by hand without one) so the UI still shows something readable
// instead of a raw URL.
function humanizeFromUrl(url: string): string | null {
  let path: string;
  try {
    path = new URL(url).pathname;
  } catch {
    return null;
  }
  const segment = path.split("/").filter(Boolean).pop();
  if (!segment) return null;
  const decoded = decodeURIComponent(segment).replace(/[-_]+/g, " ").trim();
  if (!decoded) return null;
  return decoded
    .split(" ")
    .map((word) => (word.length > 0 ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}

export function surfaceDisplayName(surface: Surface): string {
  if (surface.name && surface.name.trim()) return surface.name.trim();
  return humanizeFromUrl(surface.url) ?? TYPE_LABELS[surface.surface_type] ?? "Page";
}
