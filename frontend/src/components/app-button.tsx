import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text, ViewStyle } from "react-native";
import { usePressed } from "@/lib/use-pressed";
import { radius, spacing, usePalette } from "@/theme/tokens";
import { Chevrons } from "./shapes";

/**
 * `primary` is burnt orange and is the one loud colour in the app — keep it to
 * a single action per screen. `ink` is the near-black alternative for when a
 * submit has to be unmissable; it inverts in dark mode, where a black fill
 * would vanish into the background. `olive` is the quieter confirm, `ghost`
 * the neutral alternative, `danger` the destructive outline.
 */
type Variant = "primary" | "ink" | "olive" | "ghost" | "danger";

type Props = {
  label: string;
  onPress: () => void;
  icon?: ReactNode;
  variant?: Variant;
  disabled?: boolean;
  /** Trails the label with the fading triple chevron, for forward actions. */
  chevrons?: boolean;
  style?: ViewStyle;
};

export function AppButton({
  label,
  onPress,
  icon,
  variant = "primary",
  disabled,
  chevrons = false,
  style,
}: Props) {
  const palette = usePalette();
  const { pressed, pressHandlers } = usePressed();

  const fills: Record<Variant, ViewStyle> = {
    primary: { backgroundColor: palette.orange },
    ink: { backgroundColor: palette.ink },
    olive: { backgroundColor: palette.olive },
    ghost: {
      backgroundColor: palette.sand,
      borderWidth: 1,
      borderColor: palette.line,
    },
    danger: {
      backgroundColor: "transparent",
      borderWidth: 1,
      borderColor: palette.dangerLine,
    },
  };
  const textColors: Record<Variant, string> = {
    primary: palette.onOrange,
    // The page background reads as the inverse of ink in either theme.
    ink: palette.bg,
    olive: palette.onDark,
    ghost: palette.ink,
    danger: palette.danger,
  };
  const pressedFills: Partial<Record<Variant, string>> = {
    primary: palette.orangePressed,
    ink: palette.inkPressed,
    olive: palette.olivePressed,
    ghost: palette.sandDeep,
  };

  // Dimming the whole button to show it is disabled takes the label down with
  // it, and a half-transparent fill on the warm background leaves both barely
  // readable. A solid muted fill stays legible while still looking inert.
  const disabledFill: ViewStyle = {
    backgroundColor: palette.sand,
    borderWidth: 1,
    borderColor: palette.line,
  };
  const textColor = disabled ? palette.muted : textColors[variant];

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: Boolean(disabled) }}
      disabled={disabled}
      onPress={onPress}
      {...pressHandlers}
      style={[
        styles.button,
        disabled ? disabledFill : fills[variant],
        pressed &&
          !disabled && {
            backgroundColor:
              pressedFills[variant] ?? fills[variant].backgroundColor,
            transform: [{ scale: 0.985 }],
          },
        style,
      ]}
    >
      {icon}
      <Text style={[styles.text, { color: textColor }]}>{label}</Text>
      {chevrons ? <Chevrons color={textColor} /> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: spacing.touch,
    borderRadius: radius.field,
    paddingHorizontal: 18,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 9,
  },
  text: { fontSize: 16, fontWeight: "800" },
});
