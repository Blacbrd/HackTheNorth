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
import { SearchHits } from "@/components/search-hits";
import { Hex, NotchedSurface } from "@/components/shapes";
import { ShelfList } from "@/components/shelf-list";
import { ShelfSheet } from "@/components/shelf-sheet";
import {
  AddButton,
  Card,
  EmptyState,
  ErrorPanel,
  FilterPills,
  Kicker,
  SectionHeading,
  Sub,
  Title,
  layout,
} from "@/components/ui";
import { AppButton } from "@/components/app-button";
import { useRobotJob } from "@/hooks/use-robot-job";
import { useShelves } from "@/hooks/use-shelves";
import { findItems, greeting, isLowStock, titleCase } from "@/lib/items";
import { usePressed } from "@/lib/use-pressed";
import { useTheme } from "@/theme/theme-context";
import { radius, spacing, usePalette } from "@/theme/tokens";

type Filter = "all" | "low" | "empty";

export default function ShelvesScreen() {
  const palette = usePalette();
  const theme = useTheme();
  const themeToggle = usePressed();
  const {
    shelves,
    loading,
    error,
    refresh,
    addItem,
    removeItem,
    addShelf,
    removeShelf,
  } = useShelves();
  const [shelfError, setShelfError] = useState<string | null>(null);
  const [addingShelf, setAddingShelf] = useState(false);
  const { job } = useRobotJob();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [openShelf, setOpenShelf] = useState<number | null>(null);

  const hits = useMemo(() => findItems(shelves, query), [shelves, query]);
  const selected =
    shelves.find((shelf) => shelf.shelf_number === openShelf) ?? null;
  const searching = query.trim().length > 0;
  const robotBusy = Boolean(job?.active || job?.failure);

  const counts = useMemo(
    () => ({
      all: shelves.length,
      low: shelves.filter(isLowStock).length,
      empty: shelves.filter((shelf) => !shelf.items.length).length,
    }),
    [shelves],
  );

  const visible = useMemo(() => {
    if (filter === "low") return shelves.filter(isLowStock);
    if (filter === "empty") return shelves.filter((shelf) => !shelf.items.length);
    return shelves;
  }, [shelves, filter]);

  const nextShelfNumber =
    shelves.reduce((highest, shelf) => Math.max(highest, shelf.shelf_number), 0) + 1;

  const createShelf = async () => {
    setAddingShelf(true);
    setShelfError(null);
    try {
      const shelf = await addShelf();
      setOpenShelf(shelf.shelf_number);
    } catch (cause) {
      setShelfError(
        cause instanceof Error ? cause.message : "Could not add a shelf.",
      );
    } finally {
      setAddingShelf(false);
    }
  };

  const deleteShelf = async (shelfNumber: number) => {
    setShelfError(null);
    try {
      await removeShelf(shelfNumber);
      setOpenShelf(null);
    } catch (cause) {
      setShelfError(
        cause instanceof Error ? cause.message : "Could not remove that shelf.",
      );
    }
  };

  return (
    <SafeAreaView
      edges={["top", "left", "right"]}
      style={[layout.screen, { backgroundColor: palette.bg }]}
    >
      <ScrollView
        contentContainerStyle={layout.page}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={palette.accent}
          />
        }
      >
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <Kicker>Hampy · Inventory</Kicker>
            <Title>{greeting()}, volunteer.</Title>
            <Sub>Keep shelves current so the robot can help quickly.</Sub>
          </View>
          {/* The mark doubles as the theme switch. */}
          <Pressable
            accessibilityRole="switch"
            accessibilityState={{ checked: theme.scheme === "dark" }}
            accessibilityLabel={
              theme.scheme === "dark"
                ? "Switch to the light theme"
                : "Switch to the dark theme"
            }
            onPress={theme.toggle}
            {...themeToggle.pressHandlers}
            hitSlop={8}
            style={[themeToggle.pressed && styles.markPressed]}
          >
            <Hex size={46} color={palette.olive}>
              <MaterialCommunityIcons
                name="food-apple-outline"
                size={22}
                color={palette.onDark}
              />
            </Hex>
          </Pressable>
        </View>

        {/* The hero carries the whole reason the app exists, so it gets the
            weight: a solid olive block and the only orange button on screen. */}
        <NotchedSurface
          color={palette.heroBg}
          cornerRadius={0}
          style={styles.hero}
        >
          <View style={styles.heroTop}>
            <Hex size={58} color={palette.mustard}>
              <MaterialCommunityIcons
                name={job?.failure ? "alert-outline" : "robot-outline"}
                size={28}
                color={palette.onMustard}
              />
            </Hex>
            <View style={styles.heroText}>
              <Text style={[styles.heroTitle, { color: palette.onDark }]}>
                {job?.failure
                  ? "The robot needs you"
                  : job?.active
                    ? "Fetching your item"
                    : "Ask Hampy for an item"}
              </Text>
              <Text style={[styles.heroSub, { color: palette.onDark }]}>
                {robotBusy && job?.item
                  ? `${titleCase(job.item)} · shelf ${job.shelf_number}`
                  : robotBusy
                    ? "Tap to follow its progress"
                    : "Describe what you need — the robot fetches one that fits"}
              </Text>
            </View>
          </View>
          <AppButton
            label={robotBusy ? "Follow the robot" : "Ask Hampy"}
            onPress={() => router.push(robotBusy ? "/robot" : "/ask")}
            chevrons
            style={styles.heroCta}
          />
        </NotchedSurface>

        {!searching && shelves.length > 0 ? (
          <FilterPills<Filter>
            value={filter}
            onChange={setFilter}
            options={[
              { key: "all", label: "All shelves", count: counts.all },
              { key: "low", label: "Low stock", count: counts.low },
              { key: "empty", label: "Empty", count: counts.empty },
            ]}
          />
        ) : null}

        <View
          style={[
            styles.search,
            { backgroundColor: palette.surface, borderColor: palette.line },
          ]}
        >
          <MaterialCommunityIcons
            name="magnify"
            size={20}
            color={palette.muted}
          />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search items across every shelf"
            placeholderTextColor={palette.muted}
            style={[styles.searchInput, { color: palette.ink }]}
            accessibilityLabel="Search inventory items"
            autoCapitalize="none"
            autoCorrect={false}
          />
          {searching ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Clear search"
              onPress={() => setQuery("")}
              hitSlop={8}
            >
              <MaterialCommunityIcons
                name="close"
                size={19}
                color={palette.muted}
              />
            </Pressable>
          ) : null}
        </View>

        {error ? (
          <>
            <ErrorPanel title="Couldn’t load shelves" body={error} />
            <AppButton label="Retry" onPress={refresh} variant="ghost" />
          </>
        ) : loading && !shelves.length ? (
          <View style={styles.list}>
            {[1, 2, 3].map((key) => (
              <Card key={key} style={styles.skeleton}>
                <View
                  style={[styles.bone, { backgroundColor: palette.sand, width: "30%" }]}
                />
                <View
                  style={[styles.bone, { backgroundColor: palette.sand, width: "82%" }]}
                />
                <View
                  style={[styles.bone, { backgroundColor: palette.sand, width: "58%" }]}
                />
              </Card>
            ))}
          </View>
        ) : searching ? (
          <SearchHits hits={hits} query={query} onOpenShelf={setOpenShelf} />
        ) : !shelves.length ? (
          <EmptyState
            icon="package-variant-closed"
            title="No shelves yet"
            body="Add the first shelf, then list what is on it so the robot can reach it."
            action={
              <AppButton
                label="Add a shelf"
                onPress={createShelf}
                variant="olive"
                disabled={addingShelf}
                style={{ marginTop: 16, minWidth: 220 }}
                icon={
                  <MaterialCommunityIcons
                    name="plus"
                    size={20}
                    color={palette.onDark}
                  />
                }
              />
            }
          />
        ) : !visible.length ? (
          <EmptyState
            icon={filter === "empty" ? "package-variant-closed" : "check-circle-outline"}
            title={filter === "empty" ? "No empty shelves" : "Nothing running low"}
            body={
              filter === "empty"
                ? "Every shelf has stock the robot can reach."
                : "All shelves are well stocked right now."
            }
          />
        ) : (
          <View style={styles.listBlock}>
            <View style={styles.listHeader}>
              <SectionHeading>Shelves</SectionHeading>
              <AddButton
                label={`Add shelf ${nextShelfNumber}`}
                onPress={createShelf}
                disabled={addingShelf}
              />
            </View>
            <ShelfList shelves={visible} onOpenShelf={setOpenShelf} />
          </View>
        )}

        {shelfError ? (
          <ErrorPanel title="Couldn’t change the shelves" body={shelfError} />
        ) : null}



        {loading && shelves.length > 0 ? (
          <ActivityIndicator color={palette.accent} />
        ) : null}
      </ScrollView>

      <ShelfSheet
        key={selected?.shelf_number ?? "closed"}
        shelf={selected}
        onClose={() => setOpenShelf(null)}
        onAdd={async (item, quantity) => {
          if (selected) await addItem(selected.shelf_number, item, quantity);
        }}
        onRemove={async (item) => {
          if (selected) await removeItem(selected.shelf_number, item);
        }}
        onDeleteShelf={
          selected ? () => deleteShelf(selected.shelf_number) : undefined
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  headerCopy: { flex: 1, minWidth: 0 },
  markPressed: { transform: [{ scale: 0.92 }], opacity: 0.85 },
  hero: { padding: 20 },
  heroTop: { flexDirection: "row", alignItems: "center", gap: 14 },
  heroText: { flex: 1, minWidth: 0 },
  heroTitle: { fontSize: 18, fontWeight: "800", letterSpacing: -0.2 },
  heroSub: { fontSize: 13.5, lineHeight: 18, marginTop: 2, opacity: 0.85 },
  heroCta: { marginTop: 16 },
  search: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    height: spacing.touch,
    borderWidth: 1,
    borderRadius: radius.field,
    paddingHorizontal: 14,
  },
  searchInput: { flex: 1, fontSize: 16, minHeight: spacing.touch },
  list: { gap: 10 },
  listBlock: { gap: 10 },
  listHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  skeleton: { gap: 10 },
  bone: { height: 12, borderRadius: 6 },
});
