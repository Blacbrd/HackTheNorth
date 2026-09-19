import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text, ViewStyle } from "react-native";
import { colors, radius, spacing } from "@/theme/tokens";

type Props = {
  label: string;
  onPress: () => void;
  icon?: ReactNode;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  style?: ViewStyle;
};
export function AppButton({
  label,
  onPress,
  icon,
  variant = "primary",
  disabled,
  style,
}: Props) {
  const palette =
    variant === "danger"
      ? styles.danger
      : variant === "secondary"
        ? styles.secondary
        : styles.primary;
  const textStyle =
    variant === "secondary" ? styles.secondaryText : styles.primaryText;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        palette,
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
        style,
      ]}
    >
      {icon}
      {<Text style={[styles.text, textStyle]}>{label}</Text>}
    </Pressable>
  );
}
const styles = StyleSheet.create({
  button: {
    minHeight: spacing.touch,
    borderRadius: radius.pill,
    paddingHorizontal: 20,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },
  primary: { backgroundColor: colors.action },
  danger: { backgroundColor: colors.danger },
  secondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
  },
  text: { fontSize: 16, fontWeight: "700" },
  primaryText: { color: colors.surface },
  secondaryText: { color: colors.action },
  pressed: { transform: [{ scale: 0.98 }] },
  disabled: { opacity: 0.55 },
});
