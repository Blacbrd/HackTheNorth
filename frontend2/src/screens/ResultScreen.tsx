import { Animated, Image, StyleSheet, View } from 'react-native';

import { Button } from '../components/Button';
import { ScreenHeader } from '../components/ScreenHeader';
import { AppColors, spacing } from '../theme/tokens';

type Props = {
  colors: AppColors;
  onAgain: () => void;
  onContinue: () => void;
  originalY: Animated.Value;
  output: string;
  outputScale: Animated.Value;
  photo: string;
};

export function ResultScreen({
  colors,
  onAgain,
  onContinue,
  originalY,
  output,
  outputScale,
  photo,
}: Props) {
  return (
    <View style={styles.page}>
      <ScreenHeader
        colors={colors}
        title="Happy with it?"
        subtitle="Check that the outline still looks like your subject."
      />
      <View style={styles.compare}>
        <Animated.View style={{ transform: [{ translateY: originalY }] }}>
          <Image
            accessibilityLabel="Original photo"
            resizeMode="cover"
            source={{ uri: photo }}
            style={styles.original}
          />
        </Animated.View>
        <Animated.View
          style={[
            styles.outputFrame,
            {
              backgroundColor: '#FFFFFF',
              borderColor: colors.line,
              transform: [{ scale: outputScale }],
            },
          ]}
        >
          <Image
            accessibilityLabel="Simplified black and white drawing"
            resizeMode="contain"
            source={{ cache: 'reload', uri: output }}
            style={styles.output}
          />
        </Animated.View>
      </View>
      <View style={styles.actions}>
        <Button label="Continue!" onPress={onContinue} />
        <Button label="Take again" onPress={onAgain} tone="secondary" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, justifyContent: 'space-between', paddingHorizontal: spacing.x, paddingTop: 18 },
  compare: { flex: 1, gap: 4, justifyContent: 'center', marginVertical: 12 },
  original: { alignSelf: 'center', borderRadius: 16, height: 94, width: 94 },
  outputFrame: {
    alignSelf: 'center',
    borderRadius: 24,
    borderWidth: 1,
    flex: 1,
    maxHeight: 340,
    minHeight: 180,
    overflow: 'hidden',
    padding: 8,
    width: '100%',
  },
  output: { height: '100%', width: '100%' },
  actions: { gap: 10, paddingBottom: 4 },
});
