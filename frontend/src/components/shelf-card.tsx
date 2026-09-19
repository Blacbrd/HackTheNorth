import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import type { Shelf } from "@/types/api";
import { colors, radius } from "@/theme/tokens";

export function ShelfCard({
  shelf,
  onPress,
}: {
  shelf: Shelf;
  onPress: () => void;
}) {
  const itemLabels = useMemo(
    () =>
      Object.entries(
        shelf.items.reduce<Record<string, number>>(
          (grouped, item) => ({ ...grouped, [item]: (grouped[item] ?? 0) + 1 }),
          {},
        ),
      ),
    [shelf.items],
  );
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open shelf ${shelf.shelf_number}, ${shelf.items.length} items`}
      onPress={onPress}
      className="bg-surface border border-line rounded-card p-4 gap-4 active:scale-[0.99]"
    >
      <View style={styles.top}>
        <View>
          <Text
            className="text-muted text-xs font-extrabold"
            style={styles.eyebrow}
          >
            SHELF {shelf.shelf_number}
          </Text>
          <Text className="text-ink font-bold" style={styles.title}>
            {shelf.items.length} {shelf.items.length === 1 ? "item" : "items"}
          </Text>
        </View>
        <View className="bg-surface-muted rounded-full" style={styles.arrow}>
          <MaterialCommunityIcons
            name="chevron-right"
            size={23}
            color={colors.action}
          />
        </View>
      </View>
      <View style={styles.items}>
        {itemLabels.length ? (
          itemLabels.map(([item, quantity]) => (
            <View
              className="bg-surface-muted rounded-full"
              key={item}
              style={styles.chip}
            >
              <Text numberOfLines={1} style={styles.chipText}>
                {item}
                {quantity > 1 ? ` ×${quantity}` : ""}
              </Text>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No items yet</Text>
        )}
      </View>
    </Pressable>
  );
}
const styles = StyleSheet.create({
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  eyebrow: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  title: { color: colors.ink, fontSize: 18, fontWeight: "700", marginTop: 3 },
  arrow: {
    backgroundColor: colors.surfaceMuted,
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  items: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    backgroundColor: colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.pill,
    maxWidth: "100%",
  },
  chipText: { color: colors.ink, fontSize: 14, fontWeight: "600" },
  empty: { color: colors.muted, fontSize: 14 },
});
