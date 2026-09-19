import { Image, StyleSheet, Text, View } from 'react-native';

import { Button } from '../components/Button';
import { ScreenHeader } from '../components/ScreenHeader';
import { AppColors, spacing } from '../theme/tokens';

type Props = {
  colors: AppColors;
  error: string | null;
  onRetake: () => void;
  onSend: () => void;
  photo: string;
};

export function ReviewScreen({ colors, error, onRetake, onSend, photo }: Props) {
  return (
    <View style={styles.page}>
      <ScreenHeader
        colors={colors}
        title="Keep this one?"
        subtitle="Check the framing, then send it to make a simple drawing."
      />
      <Image
        accessibilityLabel="Selected photo"
        resizeMode="cover"
        source={{ uri: photo }}
        style={styles.photo}
      />
      <View style={styles.actions}>
        {error && (
          <Text accessibilityLiveRegion="polite" style={[styles.error, { color: colors.error }]}>
            {error}
          </Text>
        )}
        <Button label="Send" onPress={onSend} />
        <Button label="Take again" onPress={onRetake} tone="secondary" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, justifyContent: 'space-between', paddingHorizontal: spacing.x, paddingTop: 18 },
  photo: {
    borderRadius: 24,
    flex: 1,
    marginVertical: 18,
    maxHeight: 520,
    minHeight: 210,
    width: '100%',
  },
  actions: { gap: 10, paddingBottom: 4 },
  error: { fontSize: 14, lineHeight: 20, textAlign: 'center' },
});
