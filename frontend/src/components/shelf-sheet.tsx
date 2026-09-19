import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { groupItems, titleCase } from "@/lib/items";
import { radius, spacing, usePalette } from "@/theme/tokens";
import type { Shelf } from "@/types/api";
import { AppButton } from "./app-button";
import { CountPill, EmptyState, ErrorPanel, Stepper } from "./ui";

export function ShelfSheet({
  shelf,
  onClose,
  onAdd,
  onRemove,
  onDeleteShelf,
}: {
  shelf: Shelf | null;
  onClose: () => void;
  onAdd: (item: string, quantity: number) => Promise<void>;
  onRemove: (item: string) => Promise<void>;
  onDeleteShelf?: () => Promise<void>;
}) {
  const palette = usePalette();
  const [draft, setDraft] = useState("");
  const [addQuantity, setAddQuantity] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const grouped = useMemo(() => groupItems(shelf?.items ?? []), [shelf?.items]);

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try {
      await action();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "That change failed.");
    } finally {
      setBusy(null);
    }
  };

  const submit = async () => {
    const item = draft.trim().toLowerCase();
    if (!item) return;
    await run("add", () => onAdd(item, addQuantity));
    setDraft("");
    setAddQuantity(1);
  };

  /** Deleting takes the items with it, so say how many before asking. */
  const confirmDelete = () => {
    if (!shelf || !onDeleteShelf) return;
    const count = shelf.items.length;
    Alert.alert(
      `Remove shelf ${shelf.shelf_number}?`,
      count
        ? `Its ${count} item${count === 1 ? "" : "s"} will be removed with it. The robot will no longer fetch from this shelf.`
        : "The robot will no longer fetch from this shelf.",
      [
        { text: "Keep it", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () => void run("delete", onDeleteShelf),
        },
      ],
    );
  };

  return (
    <Modal
      visible={Boolean(shelf)}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Close shelf editor"
        style={[styles.scrim, { backgroundColor: palette.scrim }]}
        onPress={onClose}
      />
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.dock}
      >
        <View
          style={[
            styles.sheet,
            { backgroundColor: palette.bg, borderColor: palette.line },
          ]}
        >
          <View style={[styles.grip, { backgroundColor: palette.line }]} />
          <View style={styles.header}>
            <Text style={[styles.heading, { color: palette.ink }]}>
              Shelf {shelf?.shelf_number}
            </Text>
            <View style={styles.headerRight}>
              <CountPill>
                {shelf?.items.length ?? 0}{" "}
                {shelf?.items.length === 1 ? "item" : "items"}
              </CountPill>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Close"
                onPress={onClose}
                style={[
                  styles.close,
                  { borderColor: palette.line, backgroundColor: palette.surface },
                ]}
              >
                <MaterialCommunityIcons
                  name="close"
                  size={20}
                  color={palette.ink}
                />
              </Pressable>
            </View>
          </View>

          <ScrollView
            style={styles.body}
            contentContainerStyle={styles.bodyContent}
            keyboardShouldPersistTaps="handled"
          >
            {error ? <ErrorPanel title="Could not save" body={error} /> : null}
            {grouped.length ? (
              grouped.map((item) => (
                <View
                  key={item.name}
                  style={[styles.row, { borderBottomColor: palette.line }]}
                >
                  <Text style={[styles.name, { color: palette.ink }]}>
                    {titleCase(item.name)}
                  </Text>
                  {busy === item.name ? (
                    <ActivityIndicator color={palette.accent} />
                  ) : null}
                  <Stepper
                    label={item.name}
                    value={item.count}
                    min={0}
                    removeIconAtMin
                    busy={busy !== null}
                    onChange={(next) =>
                      run(item.name, () =>
                        next < item.count
                          ? onRemove(item.name)
                          : onAdd(item.name, 1),
                      )
                    }
                  />
                </View>
              ))
            ) : (
              <EmptyState
                icon="package-variant-closed"
                title="This shelf is empty"
                body="Add items below so the robot knows what is here."
              />
            )}
          </ScrollView>

          <View
            style={[
              styles.addBar,
              { borderTopColor: palette.line, backgroundColor: palette.bg },
            ]}
          >
            <Text style={[styles.label, { color: palette.muted }]}>
              Add to this shelf
            </Text>
            <View style={styles.addRow}>
              <View
                style={[
                  styles.field,
                  { backgroundColor: palette.surface, borderColor: palette.line },
                ]}
              >
                <TextInput
                  value={draft}
                  onChangeText={setDraft}
                  placeholder="Item name"
                  placeholderTextColor={palette.muted}
                  style={[styles.input, { color: palette.ink }]}
                  accessibilityLabel="New item name"
                  autoCapitalize="none"
                  autoCorrect={false}
                  onSubmitEditing={submit}
                  returnKeyType="done"
                />
              </View>
              <Stepper
                label="new item"
                value={addQuantity}
                min={1}
                busy={busy !== null}
                onChange={setAddQuantity}
              />
            </View>
            <AppButton
              label={busy === "add" ? "Adding…" : `Add ${addQuantity}`}
              onPress={submit}
              variant="olive"
              disabled={!draft.trim() || busy !== null}
              icon={
                <MaterialCommunityIcons
                  name="plus"
                  size={20}
                  color={palette.onDark}
                />
              }
            />
            {onDeleteShelf ? (
              <AppButton
                label={
                  busy === "delete"
                    ? "Removing…"
                    : `Remove shelf ${shelf?.shelf_number}`
                }
                onPress={confirmDelete}
                variant="danger"
                disabled={busy !== null}
                icon={
                  <MaterialCommunityIcons
                    name="trash-can-outline"
                    size={19}
                    color={palette.danger}
                  />
                }
              />
            ) : null}
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  dock: { flex: 1, justifyContent: "flex-end" },
  sheet: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    maxHeight: "86%",
  },
  grip: {
    width: 40,
    height: 4,
    borderRadius: 2,
    alignSelf: "center",
    marginTop: 10,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.page,
    paddingTop: 10,
    paddingBottom: 12,
  },
  headerRight: { flexDirection: "row", alignItems: "center", gap: 10 },
  heading: { fontSize: 20, fontWeight: "900" },
  close: {
    width: 40,
    height: 40,
    borderRadius: radius.field,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  body: { flexGrow: 0 },
  bodyContent: { paddingHorizontal: spacing.page, gap: 8, paddingBottom: 8 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    minHeight: 56,
  },
  name: { flex: 1, fontSize: 16, fontWeight: "700" },
  addBar: {
    borderTopWidth: 1,
    padding: spacing.page,
    paddingTop: 12,
    gap: 10,
  },
  label: { fontSize: 13, fontWeight: "800" },
  addRow: { flexDirection: "row", gap: 10, alignItems: "center" },
  field: {
    flex: 1,
    height: spacing.touch,
    borderWidth: 1,
    borderRadius: radius.field,
    paddingHorizontal: 14,
    justifyContent: "center",
  },
  input: { fontSize: 16, minHeight: spacing.touch },
});
