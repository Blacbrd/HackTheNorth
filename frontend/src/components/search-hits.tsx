import { Pressable, StyleSheet, Text, View } from "react-native";
import { splitMatch, titleCase } from "@/lib/items";
import { usePressed } from "@/lib/use-pressed";
import { radius, usePalette } from "@/theme/tokens";
import type { ItemHit } from "@/types/api";
import { EmptyState, Pill } from "./ui";

/**
 * Search results at item level.
 *
 * The old screen filtered whole shelves, so searching "rice" returned the
 * entire shelf and left you to find it. These rows name the item, how many
 * there are, and which shelf to walk to.
 */
export function SearchHits({
  hits,
  query,
  onOpenShelf,
}: {
  hits: ItemHit[];
  query: string;
  onOpenShelf: (shelfNumber: number) => void;
}) {
  const palette = usePalette();

  if (!hits.length) {
    return (
      <EmptyState
        icon="magnify"
        title={`No item matches “${query.trim()}”`}
        body="Check the spelling, or add it to a shelf from the shelf editor."
      />
    );
  }

  return (
    <View style={styles.list}>
      <Text style={[styles.count, { color: palette.muted }]}>
        {hits.length} {hits.length === 1 ? "match" : "matches"}
      </Text>
      {hits.map((hit) => (
        <SearchHitRow
          key={`${hit.shelfNumber}-${hit.name}`}
          hit={hit}
          query={query}
          onPress={() => onOpenShelf(hit.shelfNumber)}
        />
      ))}
    </View>
  );
}

function SearchHitRow({
  hit,
  query,
  onPress,
}: {
  hit: ItemHit;
  query: string;
  onPress: () => void;
}) {
  const palette = usePalette();
  const { pressed, pressHandlers } = usePressed();
  const parts = splitMatch(titleCase(hit.name), query);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${hit.name}, ${hit.count} on shelf ${hit.shelfNumber}`}
      onPress={onPress}
      {...pressHandlers}
      style={[
        styles.row,
        { backgroundColor: palette.surface, borderColor: palette.line },
        pressed && { backgroundColor: palette.sand },
      ]}
    >
      <Text numberOfLines={1} style={[styles.name, { color: palette.ink }]}>
        {parts.before}
        <Text
          style={{
            backgroundColor: palette.mustardSoft,
            color: palette.mustardInk,
            fontWeight: "800",
          }}
        >
          {parts.match}
        </Text>
        {parts.after}
      </Text>
      {hit.count > 1 ? (
        <Text style={[styles.qty, { color: palette.mustardInk }]}>
          {hit.count}×
        </Text>
      ) : null}
      <Pill>Shelf {hit.shelfNumber}</Pill>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  list: { gap: 10 },
  count: { fontSize: 13, fontWeight: "800", marginLeft: 2 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: radius.field,
    paddingHorizontal: 14,
    paddingVertical: 12,
    minHeight: 48,
  },
  name: { flex: 1, fontSize: 16, fontWeight: "700" },
  qty: { fontSize: 12, fontWeight: "800" },
});
