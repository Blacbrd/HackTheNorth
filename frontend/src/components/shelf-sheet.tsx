import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import type { Shelf } from "@/types/api";
import { colors, radius } from "@/theme/tokens";
import { AppButton } from "./app-button";

type Props = {
  shelf: Shelf | null;
  onClose: () => void;
  onAdd: (item: string) => Promise<void>;
  onRemove: (item: string) => Promise<void>;
};
export function ShelfSheet({ shelf, onClose, onAdd, onRemove }: Props) {
  const [item, setItem] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!shelf) return null;
  const add = async () => {
    if (!item.trim()) {
      setError("Enter an item name before adding it.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onAdd(item.trim());
      setItem("");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not add that item.",
      );
    } finally {
      setBusy(false);
    }
  };
  const remove = (value: string) =>
    Alert.alert(
      "Remove one item?",
      `Remove one ${value} from shelf ${shelf.shelf_number}?`,
      [
        { text: "Keep item", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () => {
            setBusy(true);
            setError(null);
            onRemove(value)
              .catch((cause) =>
                setError(
                  cause instanceof Error
                    ? cause.message
                    : "Could not remove that item.",
                ),
              )
              .finally(() => setBusy(false));
          },
        },
      ],
    );
  return (
    <Modal
      visible
      animationType="slide"
      transparent
      onRequestClose={onClose}
      accessibilityViewIsModal
    >
      <View style={styles.backdrop}>
        <Pressable
          style={StyleSheet.absoluteFill}
          onPress={onClose}
          accessible={false}
        />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <View style={styles.header}>
            <View>
              <Text style={styles.eyebrow}>INVENTORY EDITOR</Text>
              <Text style={styles.title}>Shelf {shelf.shelf_number}</Text>
            </View>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Close shelf editor"
              onPress={onClose}
              style={styles.close}
            >
              <MaterialCommunityIcons
                name="close"
                size={22}
                color={colors.ink}
              />
            </Pressable>
          </View>
          <View style={styles.addRow}>
            <TextInput
              value={item}
              onChangeText={setItem}
              placeholder="Add an item…"
              placeholderTextColor={colors.muted}
              style={styles.input}
              editable={!busy}
              accessibilityLabel="Item name"
              returnKeyType="done"
              onSubmitEditing={add}
            />
            <AppButton
              label={busy ? "Saving…" : "Add"}
              onPress={add}
              disabled={busy}
            />
          </View>
          {error && (
            <Text accessibilityLiveRegion="polite" style={styles.error}>
              {error}
            </Text>
          )}
          <ScrollView
            style={styles.list}
            contentContainerStyle={styles.listContent}
          >
            {shelf.items.length ? (
              shelf.items.map((entry, index) => (
                <View style={styles.row} key={`${entry}-${index}`}>
                  <Text style={styles.rowText} numberOfLines={2}>
                    {entry}
                  </Text>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={`Remove one ${entry}`}
                    onPress={() => remove(entry)}
                    disabled={busy}
                    style={styles.remove}
                  >
                    <MaterialCommunityIcons
                      name="minus"
                      size={20}
                      color={colors.danger}
                    />
                  </Pressable>
                </View>
              ))
            ) : (
              <View style={styles.empty}>
                <Text style={styles.emptyTitle}>
                  This shelf is ready for stock.
                </Text>
                <Text style={styles.emptyBody}>
                  Add the first item above to keep the robot inventory current.
                </Text>
              </View>
            )}
          </ScrollView>
          {busy && (
            <ActivityIndicator color={colors.action} style={styles.spinner} />
          )}
        </View>
      </View>
    </Modal>
  );
}
const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(22,35,26,0.35)",
    justifyContent: "flex-end",
  },
  sheet: {
    maxHeight: "82%",
    backgroundColor: colors.background,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 20,
    paddingBottom: 28,
  },
  handle: {
    alignSelf: "center",
    width: 38,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.line,
    marginTop: 10,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginVertical: 18,
  },
  eyebrow: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  title: { fontSize: 26, color: colors.ink, fontWeight: "800" },
  close: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 24,
    backgroundColor: colors.surfaceMuted,
  },
  addRow: { flexDirection: "row", gap: 8, alignItems: "center" },
  input: {
    flex: 1,
    minHeight: 48,
    borderRadius: radius.field,
    borderWidth: 1,
    borderColor: colors.line,
    paddingHorizontal: 13,
    backgroundColor: colors.surface,
    color: colors.ink,
    fontSize: 16,
  },
  error: { color: colors.danger, marginTop: 10, fontSize: 14 },
  list: { marginTop: 18 },
  listContent: { gap: 8, paddingBottom: 18 },
  row: {
    minHeight: 52,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.field,
    paddingLeft: 14,
    flexDirection: "row",
    alignItems: "center",
  },
  rowText: { flex: 1, color: colors.ink, fontSize: 16 },
  remove: {
    height: 48,
    width: 52,
    alignItems: "center",
    justifyContent: "center",
  },
  empty: {
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.card,
    padding: 18,
  },
  emptyTitle: { color: colors.ink, fontWeight: "700", fontSize: 16 },
  emptyBody: {
    color: colors.muted,
    marginTop: 5,
    fontSize: 14,
    lineHeight: 20,
  },
  spinner: { marginTop: 4 },
});
