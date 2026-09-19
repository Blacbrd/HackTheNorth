import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { groupItems, isLowStock, titleCase } from "@/lib/items";
import { usePressed } from "@/lib/use-pressed";
import { radius, usePalette } from "@/theme/tokens";
import type { Shelf } from "@/types/api";

/**
 * The shelves as one list rather than a stack of cards.
 *
 * A card per shelf spent most of its height on chrome and pushed the fourth
 * shelf off screen. A row gives the same facts — number, count, what is on it
 * — in a third of the space, so a full aisle is scannable at once.
 */
export function ShelfList({
  shelves,
  onOpenShelf,
}: {
  shelves: Shelf[];
  onOpenShelf: (shelfNumber: number) => void;
}) {
  const palette = usePalette();
  return (
    <View
      style={[
        styles.list,
        { backgroundColor: palette.surface, borderColor: palette.line },
      ]}
    >
      {shelves.map((shelf, index) => (
        <ShelfRow
          key={shelf.shelf_number}
          shelf={shelf}
          last={index === shelves.length - 1}
          onPress={() => onOpenShelf(shelf.shelf_number)}
        />
      ))}
    </View>
  );
}

function ShelfRow({
  shelf,
  last,
  onPress,
}: {
  shelf: Shelf;
  last: boolean;
  onPress: () => void;
}) {
  const palette = usePalette();
  const { pressed, pressHandlers } = usePressed();
  const grouped = useMemo(() => groupItems(shelf.items), [shelf.items]);
  const low = isLowStock(shelf);

  const preview = grouped.length
    ? grouped
        .map((item) => titleCase(item.name) + (item.count > 1 ? ` ×${item.count}` : ""))
        .join(", ")
    : "Empty — tap to add items";

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open shelf ${shelf.shelf_number}, ${shelf.items.length} items${low ? ", running low" : ""}`}
      onPress={onPress}
      {...pressHandlers}
      style={[
        styles.row,
        !last && { borderBottomWidth: 1, borderBottomColor: palette.line },
        pressed && { backgroundColor: palette.sand },
      ]}
    >
      <View
        style={[
          styles.tile,
          { backgroundColor: low ? palette.mustardSoft : palette.oliveTint },
        ]}
      >
        <Text
          style={[
            styles.tileNumber,
            { color: low ? palette.mustardInk : palette.accent },
          ]}
        >
          {shelf.shelf_number}
        </Text>
        <Text
          style={[
            styles.tileLabel,
            { color: low ? palette.mustardInk : palette.accent },
          ]}
        >
          SHELF
        </Text>
      </View>

      <View style={styles.main}>
        <View style={styles.titleRow}>
          <Text numberOfLines={1} style={[styles.name, { color: palette.ink }]}>
            Shelf {shelf.shelf_number}
          </Text>
          <Text numberOfLines={1} style={[styles.count, { color: palette.muted }]}>
            {shelf.items.length} {shelf.items.length === 1 ? "item" : "items"}
          </Text>
        </View>
        <Text
          numberOfLines={1}
          style={[styles.preview, { color: palette.muted }]}
        >
          {preview}
        </Text>
      </View>

      {low ? (
        <View style={[styles.lowTag, { backgroundColor: palette.mustardSoft }]}>
          <Text style={[styles.lowText, { color: palette.mustardInk }]}>LOW</Text>
        </View>
      ) : null}

      <MaterialCommunityIcons
        name="chevron-right"
        size={20}
        color={palette.muted}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  list: { borderWidth: 1, borderRadius: radius.card, overflow: "hidden" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    paddingHorizontal: 14,
    paddingVertical: 13,
    minHeight: 68,
  },
  tile: {
    width: 42,
    height: 42,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  tileNumber: { fontSize: 19, fontWeight: "900", lineHeight: 21 },
  tileLabel: { fontSize: 8, fontWeight: "800", letterSpacing: 0.8, opacity: 0.75 },
  main: { flex: 1, minWidth: 0 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  name: { fontSize: 16, fontWeight: "800", flexShrink: 1 },
  count: { fontSize: 12.5, fontWeight: "700", flexShrink: 0 },
  preview: { fontSize: 13, marginTop: 2 },
  lowTag: {
    borderRadius: radius.pill,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  lowText: { fontSize: 10.5, fontWeight: "800", letterSpacing: 0.6 },
});
