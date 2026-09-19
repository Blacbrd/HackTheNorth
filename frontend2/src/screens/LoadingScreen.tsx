import { ActivityIndicator, Image, StyleSheet, Text, View } from 'react-native';

import { ScreenHeader } from '../components/ScreenHeader';
import { AppColors, spacing } from '../theme/tokens';

type Props = {
  colors: AppColors;
  photo?: string;
};

export function LoadingScreen({ colors, photo }: Props) {
  return (
    <View style={styles.page}>
      <ScreenHeader
        colors={colors}
        title="Finding the main shape"
        subtitle="Your photo is being reduced to a clear, drawable outline."
      />
      <View style={styles.loadingPreview}>
        {photo && <Image resizeMode="cover" source={{ uri: photo }} style={styles.photo} />}
        <View style={[styles.loadingCard, { backgroundColor: colors.surface }]}>
          <ActivityIndicator accessibilityLabel="Simplifying photo" size="large" color={colors.accent} />
          <Text style={[styles.loadingText, { color: colors.text }]}>Simplifying your subject</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, paddingHorizontal: spacing.x, paddingTop: 18 },
  loadingPreview: { flex: 1, justifyContent: 'center', marginTop: 18 },
  photo: { borderRadius: 24, height: '90%', opacity: 0.24, width: '100%' },
  loadingCard: {
    alignItems: 'center',
    alignSelf: 'center',
    borderRadius: 20,
    gap: 14,
    padding: 24,
    position: 'absolute',
  },
  loadingText: { fontSize: 16, fontWeight: '700' },
});
