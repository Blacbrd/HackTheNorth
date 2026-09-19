import { StyleSheet, Text, View } from 'react-native';

import { AppColors } from '../theme/tokens';

type Props = {
  colors: AppColors;
  title: string;
  subtitle: string;
};

export function ScreenHeader({ colors, title, subtitle }: Props) {
  return (
    <View style={styles.header}>
      <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
      <Text style={[styles.copy, { color: colors.muted }]}>{subtitle}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: 7 },
  title: { fontSize: 34, fontWeight: '800', letterSpacing: -1.1 },
  copy: { fontSize: 16, lineHeight: 23, maxWidth: 340 },
});
