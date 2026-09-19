import type { GroupedItem, ItemHit, Shelf } from "@/types/api";

/**
 * Collapse a shelf's flat list into names with counts.
 *
 * A shelf stores two bananas as the literal list ["banana", "banana"], so the
 * count only exists once the repeats are folded together here.
 */
export function groupItems(items: string[]): GroupedItem[] {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(item, (counts.get(item) ?? 0) + 1);
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Below this many items a shelf is flagged as running low. */
export const LOW_STOCK_THRESHOLD = 4;

/**
 * Whether a shelf needs restocking soon.
 *
 * Empty is deliberately not low: an empty shelf is its own state with its own
 * filter, and lumping the two together would hide the shelves that still have
 * something on them but are about to run out.
 */
export function isLowStock(shelf: Shelf): boolean {
  return shelf.items.length > 0 && shelf.items.length < LOW_STOCK_THRESHOLD;
}

/** Every matching item across every shelf, so search points at items not shelves. */
export function findItems(shelves: Shelf[], query: string): ItemHit[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  return shelves.flatMap((shelf) =>
    groupItems(shelf.items)
      .filter((item) => item.name.toLowerCase().includes(needle))
      .map((item) => ({ ...item, shelfNumber: shelf.shelf_number })),
  );
}

/** Split a label around the matched run so the hit can be highlighted. */
export function splitMatch(
  name: string,
  query: string,
): { before: string; match: string; after: string } {
  const needle = query.trim().toLowerCase();
  const at = needle ? name.toLowerCase().indexOf(needle) : -1;
  if (at < 0) return { before: name, match: "", after: "" };
  return {
    before: name.slice(0, at),
    match: name.slice(at, at + needle.length),
    after: name.slice(at + needle.length),
  };
}

export function titleCase(value: string): string {
  return value.replace(/\b\w/g, (character) => character.toUpperCase());
}

export function greeting(now = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function formatElapsed(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function timeAgo(iso: string, now = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
