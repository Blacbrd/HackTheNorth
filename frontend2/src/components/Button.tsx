import { Pressable, StyleProp, StyleSheet, Text, useColorScheme, ViewStyle } from 'react-native';
import { palette } from '../theme/tokens';

type Props = {
  label: string;
  onPress: () => void;
  tone?: 'primary' | 'secondary';
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Button({ label, onPress, tone = 'primary', disabled, style }: Props) {
  const colors = palette(useColorScheme());
  const toneStyle = tone === 'primary' ? { backgroundColor: colors.accent } : tone === 'secondary' ? { backgroundColor: colors.surface, borderColor: colors.line, borderWidth: 1 } : undefined;
  return <Pressable accessibilityRole="button" accessibilityLabel={label} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.base, toneStyle, disabled && styles.disabled, pressed && !disabled && styles.pressed, style]}>
    <Text style={[styles.label, { color: tone === 'primary' ? colors.onAccent : colors.text }]}>{label}</Text>
  </Pressable>;
}

const styles = StyleSheet.create({
  base: { minHeight: 52, paddingHorizontal: 20, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  label: { fontSize: 16, fontWeight: '700' }, disabled: { opacity: 0.5 }, pressed: { transform: [{ scale: 0.98 }] }
});
