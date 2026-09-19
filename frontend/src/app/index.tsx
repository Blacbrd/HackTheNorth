import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppButton } from "@/components/app-button";
import { ShelfCard } from "@/components/shelf-card";
import { ShelfSheet } from "@/components/shelf-sheet";
import { useShelves } from "@/hooks/use-shelves";
import { colors, radius } from "@/theme/tokens";

export default function ShelvesScreen() {
  const { shelves, loading, error, refresh, addItem, removeItem } =
    useShelves();
  const [query, setQuery] = useState("");
  const [selectedShelfNumber, setSelectedShelfNumber] = useState<number | null>(
    null,
  );
  const filtered = useMemo(
    () =>
      shelves.filter(
        (shelf) =>
          shelf.items.some((item) =>
            item.toLowerCase().includes(query.trim().toLowerCase()),
          ) || !query.trim(),
      ),
    [shelves, query],
  );
  const selected =
    shelves.find((shelf) => shelf.shelf_number === selectedShelfNumber) ?? null;
  return (
    <SafeAreaView className="flex-1 bg-canvas" style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={colors.action}
          />
        }
      >
        <View
          className="flex-row items-start justify-between"
          style={styles.header}
        >
          <View style={styles.headerCopy}>
            <Text
              className="text-action text-xs font-extrabold tracking-widest"
              style={styles.kicker}
            >
              HAMPY · INVENTORY
            </Text>
            <Text
              className="text-ink text-3xl font-extrabold"
              style={styles.title}
            >
              Good morning, volunteer.
            </Text>
            <Text className="text-muted text-base" style={styles.subtitle}>
              Keep shelves current so the robot can help quickly.
            </Text>
          </View>
          <View className="bg-surface-muted rounded-full" style={styles.mark}>
            <MaterialCommunityIcons
              name="food-apple-outline"
              size={27}
              color={colors.action}
            />
          </View>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Ask Hampy to choose an item"
          onPress={() => router.push("/ask")}
          className="bg-surface border border-line rounded-card flex-row items-center p-3.5 gap-3 active:scale-[0.99]"
        >
          <View className="bg-action rounded-full" style={styles.askIcon}>
            <MaterialCommunityIcons
              name="robot-outline"
              size={25}
              color={colors.surface}
            />
          </View>
          <View style={styles.askText}>
            <Text className="text-ink font-extrabold" style={styles.askTitle}>
              Ask Hampy
            </Text>
            <Text className="text-muted" style={styles.askBody}>
              Find the best item for a request
            </Text>
          </View>
          <MaterialCommunityIcons
            name="arrow-right"
            size={21}
            color={colors.action}
          />
        </Pressable>
        <Text className="text-ink font-extrabold" style={styles.sectionTitle}>
          Shelves
        </Text>
        <View
          className="bg-surface border border-line rounded-field flex-row items-center"
          style={styles.search}
        >
          <MaterialCommunityIcons
            name="magnify"
            size={21}
            color={colors.muted}
          />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search items…"
            placeholderTextColor={colors.muted}
            style={styles.searchInput}
            accessibilityLabel="Search inventory items"
            autoCorrect={false}
          />
        </View>
        {loading && !shelves.length ? (
          <View style={styles.skeletons}>
            {[1, 2, 3].map((number) => (
              <View
                className="bg-surface-muted rounded-card"
                key={number}
                style={styles.skeleton}
              />
            ))}
          </View>
        ) : error ? (
          <View style={styles.state}>
            <Text style={styles.stateTitle}>Couldn’t load shelves</Text>
            <Text style={styles.stateBody}>{error}</Text>
            <AppButton label="Retry" onPress={refresh} />
          </View>
        ) : !shelves.length ? (
          <View style={styles.state}>
            <Text style={styles.stateTitle}>No shelves yet</Text>
            <Text style={styles.stateBody}>
              Inventory will appear here when the storage file has shelves.
            </Text>
          </View>
        ) : !filtered.length ? (
          <View style={styles.state}>
            <Text style={styles.stateTitle}>No matching items</Text>
            <Text style={styles.stateBody}>
              Try a different item name or clear the search.
            </Text>
            <AppButton
              label="Clear Search"
              variant="secondary"
              onPress={() => setQuery("")}
            />
          </View>
        ) : (
          <View style={styles.list}>
            {filtered.map((shelf) => (
              <ShelfCard
                key={shelf.shelf_number}
                shelf={shelf}
                onPress={() => setSelectedShelfNumber(shelf.shelf_number)}
              />
            ))}
          </View>
        )}
        {loading && shelves.length > 0 && (
          <ActivityIndicator color={colors.action} />
        )}
      </ScrollView>
      <ShelfSheet
        key={selected?.shelf_number ?? "closed"}
        shelf={selected}
        onClose={() => setSelectedShelfNumber(null)}
        onAdd={async (item) => {
          if (!selected) return;
          await addItem(selected.shelf_number, item);
        }}
        onRemove={async (item) => {
          if (!selected) return;
          await removeItem(selected.shelf_number, item);
        }}
      />
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: {
    padding: 20,
    paddingBottom: 36,
    width: "100%",
    maxWidth: 680,
    alignSelf: "center",
    gap: 18,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginTop: 5,
  },
  headerCopy: { flex: 1, minWidth: 0, paddingRight: 12 },
  kicker: {
    color: colors.action,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1,
  },
  title: {
    color: colors.ink,
    fontSize: 30,
    fontWeight: "800",
    lineHeight: 36,
    marginTop: 5,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 16,
    lineHeight: 23,
    marginTop: 5,
    maxWidth: 290,
  },
  mark: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.surfaceMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  askIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.action,
  },
  askText: { flex: 1 },
  askTitle: { color: colors.ink, fontSize: 17, fontWeight: "800" },
  askBody: { color: colors.muted, fontSize: 14, marginTop: 2 },
  sectionTitle: {
    color: colors.ink,
    fontSize: 21,
    fontWeight: "800",
    marginTop: 5,
  },
  search: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    borderRadius: radius.field,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.surface,
    paddingHorizontal: 13,
  },
  searchInput: { color: colors.ink, flex: 1, fontSize: 16, minHeight: 48 },
  list: { gap: 10 },
  skeletons: { gap: 10 },
  skeleton: {
    height: 130,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.card,
  },
  state: {
    gap: 9,
    borderRadius: radius.card,
    backgroundColor: colors.surfaceMuted,
    padding: 20,
    alignItems: "flex-start",
  },
  stateTitle: { color: colors.ink, fontSize: 18, fontWeight: "800" },
  stateBody: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 21,
    marginBottom: 4,
  },
});
