import { RefObject, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { CameraType, CameraView } from 'expo-camera';

import { Button } from '../components/Button';
import { AppColors } from '../theme/tokens';
import { CameraPermission } from '../types';

type Props = {
  cameraRef: RefObject<CameraView | null>;
  colors: AppColors;
  error: string | null;
  facing: CameraType;
  onCapture: () => void;
  onChoose: () => void;
  onFlip: () => void;
  permission: CameraPermission | null;
  requestPermission: () => Promise<unknown>;
};

export function CameraScreen({
  cameraRef,
  colors,
  error,
  facing,
  onCapture,
  onChoose,
  onFlip,
  permission,
  requestPermission,
}: Props) {
  const [isReady, setIsReady] = useState(false);
  const [mountError, setMountError] = useState<string | null>(null);

  useEffect(() => setIsReady(false), [facing]);

  if (!permission) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={[styles.permission, { backgroundColor: colors.background }]}>
        <Text style={[styles.permissionTitle, { color: colors.text }]}>Take a picture</Text>
        <Text style={[styles.permissionCopy, { color: colors.muted }]}>
          Use the camera or choose a photo that already exists on your device.
        </Text>
        <View style={styles.permissionActions}>
          <Button
            label={permission.canAskAgain ? 'Allow camera access' : 'Open settings'}
            onPress={() => {
              if (permission.canAskAgain) void requestPermission();
              else void Linking.openSettings();
            }}
          />
          <Button label="Choose from library" onPress={onChoose} tone="secondary" />
        </View>
        {error && (
          <Text accessibilityLiveRegion="polite" style={[styles.error, { color: colors.error }]}>
            {error}
          </Text>
        )}
      </View>
    );
  }

  return (
    <View style={[styles.cameraPage, { backgroundColor: colors.camera }]}>
      <CameraView
        facing={facing}
        onCameraReady={() => setIsReady(true)}
        onMountError={({ message }) => setMountError(message)}
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.cameraScrim}>
        <View>
          <Text style={styles.brand}>PICTURE TO PATH</Text>
          <Text style={styles.cameraTitle}>Take a picture</Text>
          <Text style={styles.cameraCopy}>Frame one clear subject in the middle.</Text>
        </View>
        <View>
          {(error || mountError) && (
            <Text accessibilityLiveRegion="polite" style={styles.cameraError}>
              {error || 'The camera could not start. You can still choose a photo.'}
            </Text>
          )}
          <View style={styles.cameraControls}>
            <Pressable
              accessibilityHint="Opens your device photo library"
              accessibilityLabel="Choose a photo from your library"
              accessibilityRole="button"
              onPress={onChoose}
              style={({ pressed }) => [styles.smallCameraButton, pressed && styles.pressed]}
            >
              <Text style={styles.cameraButtonText}>Library</Text>
            </Pressable>
            <Pressable
              accessibilityLabel="Take picture"
              accessibilityRole="button"
              disabled={!isReady || Boolean(mountError)}
              onPress={onCapture}
              style={({ pressed }) => [
                styles.shutter,
                (!isReady || mountError) && styles.disabled,
                pressed && styles.pressed,
              ]}
            >
              <View style={styles.shutterInner} />
            </Pressable>
            <Pressable
              accessibilityLabel="Switch camera"
              accessibilityRole="button"
              onPress={onFlip}
              style={({ pressed }) => [styles.smallCameraButton, pressed && styles.pressed]}
            >
              <Text style={styles.cameraButtonText}>Flip</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  permission: { flex: 1, gap: 16, justifyContent: 'center', padding: 28 },
  permissionTitle: { fontSize: 36, fontWeight: '800', letterSpacing: -1.2 },
  permissionCopy: { fontSize: 16, lineHeight: 23, maxWidth: 340 },
  permissionActions: { gap: 10, marginTop: 8 },
  error: { fontSize: 14, lineHeight: 20, textAlign: 'center' },
  cameraPage: { flex: 1, overflow: 'hidden' },
  cameraScrim: {
    flex: 1,
    justifyContent: 'space-between',
    padding: 24,
    paddingTop: 26,
    backgroundColor: 'rgba(0,0,0,0.22)',
  },
  brand: { color: '#D7F5BC', fontSize: 12, fontWeight: '800', letterSpacing: 1.5 },
  cameraTitle: {
    color: '#FFFFFF',
    fontSize: 35,
    fontWeight: '800',
    letterSpacing: -1.1,
    marginTop: 8,
  },
  cameraCopy: { color: '#FFFFFF', fontSize: 16, marginTop: 7, opacity: 0.9 },
  cameraError: {
    alignSelf: 'center',
    color: '#FFFFFF',
    fontSize: 14,
    lineHeight: 19,
    marginBottom: 12,
    maxWidth: 300,
    textAlign: 'center',
  },
  cameraControls: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  smallCameraButton: {
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.55)',
    borderColor: 'rgba(255,255,255,0.45)',
    borderRadius: 22,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 44,
    width: 72,
  },
  cameraButtonText: { color: '#FFFFFF', fontWeight: '700' },
  shutter: {
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 39,
    height: 78,
    padding: 6,
    width: 78,
  },
  shutterInner: { backgroundColor: '#FFFFFF', borderRadius: 99, flex: 1 },
  disabled: { opacity: 0.48 },
  pressed: { transform: [{ scale: 0.97 }] },
});
