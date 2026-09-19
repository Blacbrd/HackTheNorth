import { useCallback, useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Alert, Animated, Platform, useColorScheme } from 'react-native';
import { CameraType, CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { CameraScreen } from './src/screens/CameraScreen';
import { LoadingScreen } from './src/screens/LoadingScreen';
import { ResultScreen } from './src/screens/ResultScreen';
import { ReviewScreen } from './src/screens/ReviewScreen';
import { disposeSimplifiedImage, simplifyImage } from './src/services/simplify';
import { palette } from './src/theme/tokens';
import { Photo } from './src/types';

type Stage = 'camera' | 'review' | 'loading' | 'result';

function App() {
  const scheme = useColorScheme();
  const colors = palette(scheme);
  const camera = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [stage, setStage] = useState<Stage>('camera');
  const [facing, setFacing] = useState<CameraType>('back');
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const originalY = useRef(new Animated.Value(0)).current;
  const outputScale = useRef(new Animated.Value(0.92)).current;

  useEffect(() => {
    if (stage !== 'result') return;

    let cancelled = false;
    let animation: Animated.CompositeAnimation | undefined;
    AccessibilityInfo.isReduceMotionEnabled().then((reduceMotion) => {
      if (cancelled) return;
      if (reduceMotion) {
        originalY.setValue(-4);
        outputScale.setValue(1);
        return;
      }

      const useNativeDriver = Platform.OS !== 'web';
      animation = Animated.parallel([
        Animated.timing(originalY, {
          toValue: -8,
          duration: 360,
          useNativeDriver,
        }),
        Animated.spring(outputScale, {
          toValue: 1,
          friction: 8,
          useNativeDriver,
        }),
      ]);
      animation.start();
    });

    return () => {
      cancelled = true;
      animation?.stop();
    };
  }, [stage, originalY, outputScale]);

  useEffect(
    () => () => {
      if (output) disposeSimplifiedImage(output);
    },
    [output],
  );

  const selectPhoto = useCallback((nextPhoto: Photo) => {
    setPhoto(nextPhoto);
    setError(null);
    setStage('review');
  }, []);

  const takePhoto = useCallback(async () => {
    setError(null);
    try {
      const captured = await camera.current?.takePictureAsync({ quality: 0.85 });
      if (captured) selectPhoto({ uri: captured.uri, mimeType: 'image/jpeg' });
    } catch {
      setError('The camera could not take that picture. Please try again.');
    }
  }, [selectPhoto]);

  const choosePhoto = useCallback(async () => {
    setError(null);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        quality: 0.85,
      });
      if (!result.canceled) {
        const selected = result.assets[0];
        selectPhoto({ uri: selected.uri, mimeType: selected.mimeType });
      }
    } catch {
      setError('The photo library could not be opened. Please try again.');
    }
  }, [selectPhoto]);

  const sendPhoto = useCallback(async () => {
    if (!photo) return;

    setStage('loading');
    setError(null);
    try {
      const result = await simplifyImage(photo.uri, photo.mimeType);
      setOutput(result.uri);
      originalY.setValue(0);
      outputScale.setValue(0.92);
      setStage('result');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong.');
      setStage('review');
    }
  }, [photo, originalY, outputScale]);

  const startAgain = useCallback(() => {
    setPhoto(null);
    setOutput(null);
    setError(null);
    setStage('camera');
  }, []);

  return (
    <SafeAreaProvider>
      <SafeAreaView
        style={{ flex: 1, backgroundColor: colors.background }}
        edges={['top', 'bottom']}
      >
        <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
        {stage === 'camera' && (
          <CameraScreen
            cameraRef={camera}
            colors={colors}
            error={error}
            facing={facing}
            onCapture={takePhoto}
            onChoose={choosePhoto}
            onFlip={() => setFacing((value) => (value === 'back' ? 'front' : 'back'))}
            permission={permission}
            requestPermission={requestPermission}
          />
        )}
        {stage === 'review' && photo && (
          <ReviewScreen
            colors={colors}
            error={error}
            onRetake={startAgain}
            onSend={sendPhoto}
            photo={photo.uri}
          />
        )}
        {stage === 'loading' && <LoadingScreen colors={colors} photo={photo?.uri} />}
        {stage === 'result' && photo && output && (
          <ResultScreen
            colors={colors}
            onAgain={startAgain}
            onContinue={() =>
              Alert.alert(
                'Ready for the robot',
                'Your simplified drawing is ready for the next step.',
              )
            }
            originalY={originalY}
            output={output}
            outputScale={outputScale}
            photo={photo.uri}
          />
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

export default App;
