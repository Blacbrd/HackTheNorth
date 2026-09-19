import type { ReactNode } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  ViewStyle,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { usePressed } from "@/lib/use-pressed";
import { radius, spacing, type, usePalette } from "@/theme/tokens";
import { Hex } from "./shapes";

/** Small shared pieces so the four screens stay consistent without repeating styles. */

export function Kicker({ children }: { children: string }) {
  const palette = usePalette();
  // Mustard itself is too light against the cream base to carry 11.5px text,
  // so the kicker uses the darker ink from the same family.
  return (
    <Text style={[styles.kicker, { color: palette.mustardInk }]}>
      {children.toUpperCase()}
    </Text>
  );
}

export function Title({ children }: { children: ReactNode }) {
  const palette = usePalette();
  return <Text style={[styles.title, { color: palette.ink }]}>{children}</Text>;
}

export function Sub({ children }: { children: ReactNode }) {
  const palette = usePalette();
  return <Text style={[styles.sub, { color: palette.muted }]}>{children}</Text>;
}

export function SectionHeading({ children }: { children: ReactNode }) {
  const palette = usePalette();
  return <Text style={[styles.section, { color: palette.ink }]}>{children}</Text>;
}

export function Help({ children }: { children: ReactNode }) {
  const palette = usePalette();
  return <Text style={[styles.help, { color: palette.muted }]}>{children}</Text>;
}

export function Card({
  children,
  style,
}: {
  children: ReactNode;
  style?: ViewStyle;
}) {
  const palette = usePalette();
  return (
    <View
      style={[
        styles.card,
        { backgroundColor: palette.surface, borderColor: palette.line },
        style,
      ]}
    >
      {children}
    </View>
  );
}

/** The olive location badge: "Shelf 3" on a search hit or the robot's target. */
export function Pill({ children }: { children: ReactNode }) {
  const palette = usePalette();
  return (
    <View style={[styles.pill, { backgroundColor: palette.olive }]}>
      <Text style={[styles.pillText, { color: palette.onDark }]}>{children}</Text>
    </View>
  );
}

/** The mustard count badge, for quantities rather than places. */
export function CountPill({ children }: { children: ReactNode }) {
  const palette = usePalette();
  return (
    <View style={[styles.pill, { backgroundColor: palette.mustardSoft }]}>
      <Text style={[styles.pillText, { color: palette.mustardInk }]}>
        {children}
      </Text>
    </View>
  );
}

/**
 * The All / Low stock / Empty row above the shelf list.
 *
 * It earns its place once there are more than a couple of shelves: the counts
 * are the fastest read of whether anything needs restocking.
 */
export function FilterPills<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { key: T; label: string; count: number }[];
  value: T;
  onChange: (next: T) => void;
}) {
  const palette = usePalette();
  return (
    // The row scrolls sideways rather than compressing: a pill that shrinks
    // wraps its label onto two lines and the whole row looks squashed.
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.pillRow}
      style={styles.pillScroll}
    >
      {options.map((option) => {
        const selected = option.key === value;
        return (
          <Pressable
            key={option.key}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            accessibilityLabel={`${option.label}, ${option.count}`}
            onPress={() => onChange(option.key)}
            style={[
              styles.filterPill,
              {
                backgroundColor: selected ? palette.mustard : palette.surface,
                borderColor: selected ? palette.mustard : palette.line,
              },
            ]}
          >
            <Text
              numberOfLines={1}
              style={[
                styles.filterLabel,
                { color: selected ? palette.onMustard : palette.muted },
              ]}
            >
              {option.label}
            </Text>
            <Text
              numberOfLines={1}
              style={[
                styles.filterCount,
                { color: selected ? palette.onMustard : palette.muted },
              ]}
            >
              {option.count}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export function ErrorPanel({ title, body }: { title: string; body?: string }) {
  const palette = usePalette();
  return (
    <View
      accessibilityLiveRegion="polite"
      style={[
        styles.error,
        { backgroundColor: palette.dangerSoft, borderColor: palette.dangerLine },
      ]}
    >
      <MaterialCommunityIcons
        name="alert-circle-outline"
        size={21}
        color={palette.danger}
      />
      <View style={styles.errorText}>
        <Text style={[styles.errorTitle, { color: palette.ink }]}>{title}</Text>
        {body ? (
          <Text style={[styles.errorBody, { color: palette.muted }]}>{body}</Text>
        ) : null}
      </View>
    </View>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: keyof typeof MaterialCommunityIcons.glyphMap;
  title: string;
  body: string;
  action?: ReactNode;
}) {
  const palette = usePalette();
  return (
    <View style={styles.empty}>
      <Hex size={66} color={palette.oliveTint} style={styles.emptyIcon}>
        <MaterialCommunityIcons name={icon} size={28} color={palette.accent} />
      </Hex>
      <Text style={[styles.emptyTitle, { color: palette.ink }]}>{title}</Text>
      <Text style={[styles.emptyBody, { color: palette.muted }]}>{body}</Text>
      {action}
    </View>
  );
}

/**
 * The + beside the "Shelves" heading.
 *
 * There is no matching − : removing is done from inside a shelf, where you can
 * see what is on the one you are about to delete.
 */
export function AddButton({
  label,
  onPress,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  const palette = usePalette();
  const { pressed, pressHandlers } = usePressed();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      {...pressHandlers}
      style={[
        styles.addButton,
        {
          borderColor: palette.line,
          backgroundColor:
            pressed && !disabled ? palette.sand : palette.surface,
        },
      ]}
    >
      <MaterialCommunityIcons
        name="plus"
        size={22}
        color={disabled ? palette.muted : palette.accent}
      />
    </Pressable>
  );
}

/** A +/− control. Quantity is repetition in the store, so this is the fix for
 *  adding five of something without five separate taps. */
export function Stepper({
  value,
  onChange,
  min = 0,
  label,
  removeIconAtMin = false,
  busy = false,
}: {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  label: string;
  removeIconAtMin?: boolean;
  busy?: boolean;
}) {
  const palette = usePalette();
  const atMin = value <= min + (removeIconAtMin ? 1 : 0);
  return (
    <View
      accessibilityRole="adjustable"
      accessibilityLabel={`${label} quantity`}
      accessibilityValue={{ now: value }}
      style={[
        styles.stepper,
        { borderColor: palette.line, backgroundColor: palette.surface },
      ]}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={
          removeIconAtMin && atMin ? `Remove ${label}` : `One fewer ${label}`
        }
        disabled={busy || value <= min}
        onPress={() => onChange(value - 1)}
        style={styles.stepButton}
      >
        <MaterialCommunityIcons
          name={removeIconAtMin && atMin ? "trash-can-outline" : "minus"}
          size={20}
          color={value <= min ? palette.muted : palette.accent}
        />
      </Pressable>
      <Text style={[styles.stepValue, { color: palette.ink }]}>{value}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`One more ${label}`}
        disabled={busy}
        onPress={() => onChange(value + 1)}
        style={styles.stepButton}
      >
        <MaterialCommunityIcons name="plus" size={20} color={palette.accent} />
      </Pressable>
    </View>
  );
}

export const styles = StyleSheet.create({
  kicker: { ...type.kicker },
  title: { ...type.title, marginTop: 5 },
  sub: { ...type.body, marginTop: 4 },
  section: { ...type.section },
  help: { ...type.help },
  card: { borderRadius: radius.card, borderWidth: 1, padding: 16 },
  pill: {
    borderRadius: radius.pill,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  pillText: { fontSize: 13, fontWeight: "800" },
  // `flexGrow: 0` keeps the horizontal ScrollView from claiming spare
  // vertical space in the page's flex column.
  pillScroll: { flexGrow: 0, marginHorizontal: -spacing.page },
  pillRow: { flexDirection: "row", gap: 8, paddingHorizontal: spacing.page },
  filterPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flexShrink: 0,
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: 15,
    paddingVertical: 9,
  },
  filterLabel: { fontSize: 13.5, fontWeight: "800" },
  filterCount: { fontSize: 11, fontWeight: "800", opacity: 0.75 },
  error: {
    flexDirection: "row",
    gap: 12,
    padding: 14,
    borderRadius: radius.card,
    borderWidth: 1,
    alignItems: "flex-start",
  },
  errorText: { flex: 1, minWidth: 0 },
  errorTitle: { fontSize: 15, fontWeight: "800" },
  errorBody: { fontSize: 14, lineHeight: 20, marginTop: 3 },
  empty: { alignItems: "center", paddingVertical: 38, paddingHorizontal: 20 },
  emptyIcon: { marginBottom: 14 },
  emptyTitle: { fontSize: 17, fontWeight: "800" },
  emptyBody: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
    maxWidth: 280,
    marginTop: 6,
  },
  stepper: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: radius.pill,
    overflow: "hidden",
  },
  stepButton: {
    width: 44,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
  },
  addButton: {
    width: 54,
    height: 44,
    borderWidth: 1,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  stepValue: {
    minWidth: 26,
    textAlign: "center",
    fontWeight: "900",
    fontSize: 15,
  },
});

export const layout = StyleSheet.create({
  screen: { flex: 1 },
  page: {
    width: "100%",
    maxWidth: 680,
    alignSelf: "center",
    padding: spacing.page,
    paddingBottom: 36,
    gap: 16,
  },
});
