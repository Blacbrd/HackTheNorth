import { useEffect, useState } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  Animated,
  Easing,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppButton } from "@/components/app-button";
import { Hex, NotchedSurface } from "@/components/shapes";
import { Card, ErrorPanel, Help, Kicker, Title, layout } from "@/components/ui";
import { useVoiceRequest } from "@/hooks/use-voice-request";
import { usePressed } from "@/lib/use-pressed";
import { recommendationApi } from "@/services/api";
import { radius, usePalette } from "@/theme/tokens";

const MAX_LENGTH = 700;
const MIC_SIZE = 118;

export default function AskScreen() {
  const palette = usePalette();
  const mic = usePressed();
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const voice = useVoiceRequest((text) =>
    setRequest((current) => (current ? `${current} ${text}` : text)),
  );

  const listening = voice.status === "recording";
  const transcribing = voice.status === "transcribing";
  const changing = voice.status === "starting" || voice.status === "stopping";
  const locked = busy || transcribing || changing;

  const submit = async () => {
    if (!request.trim()) {
      setError("Describe what you need so Hampy can choose an item.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await recommendationApi.ask(request.trim());
      setRequest("");
      router.push("/robot");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Hampy could not choose an item.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView
      edges={["top", "left", "right"]}
      style={[layout.screen, { backgroundColor: palette.bg }]}
    >
      <ScrollView
        contentContainerStyle={layout.page}
        keyboardShouldPersistTaps="handled"
      >
        <View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Back to shelves"
            onPress={() => router.push("/")}
            style={styles.back}
            hitSlop={6}
          >
            <MaterialCommunityIcons
              name="arrow-left"
              size={19}
              color={palette.accent}
            />
            <Text style={[styles.backText, { color: palette.accent }]}>
              Shelves
            </Text>
          </Pressable>
          <Kicker>Ask Hampy</Kicker>
          <Title>What should the robot bring?</Title>
        </View>

        {/* Voice leads: a volunteer holding a crate can speak but not type. */}
        <NotchedSurface
          color={palette.oliveTint}
          borderColor={palette.line}
          style={styles.askCard}
        >
          <View style={styles.micWrap}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={
                listening ? "Stop recording" : "Record your request"
              }
              accessibilityState={{ busy: listening }}
              onPress={voice.toggle}
              disabled={locked && !listening}
              {...mic.pressHandlers}
              style={[
                styles.micHit,
                { opacity: locked && !listening ? 0.5 : 1 },
                mic.pressed && { transform: [{ scale: 0.97 }] },
              ]}
            >
              {listening ? <MicPulse color={palette.orange} /> : null}
              <Hex
                size={MIC_SIZE}
                color={listening ? palette.orange : palette.olive}
              >
                <MaterialCommunityIcons
                  name={listening ? "stop" : "microphone-outline"}
                  size={42}
                  color={listening ? palette.onOrange : palette.onDark}
                />
              </Hex>
            </Pressable>

            {listening ? (
              <View style={styles.recRow}>
                <View style={[styles.recDot, { backgroundColor: palette.orange }]} />
                <Text style={[styles.recText, { color: palette.orange }]}>
                  Listening… tap to stop
                </Text>
              </View>
            ) : (
              <Text style={[styles.micCaption, { color: palette.ink }]}>
                {transcribing
                  ? "Transcribing…"
                  : changing
                    ? "Preparing the microphone…"
                    : "Tap and speak"}
              </Text>
            )}
            <Text style={[styles.micSub, { color: palette.muted }]}>
              {listening
                ? "Your words are transcribed into the box below."
                : "Say what you need — “something vegetarian”, “a gluten-free dinner”."}
            </Text>
          </View>

          <View
            style={[
              styles.inputBox,
              { backgroundColor: palette.surface, borderColor: palette.line },
            ]}
          >
            <TextInput
              value={request}
              onChangeText={setRequest}
              multiline
              textAlignVertical="top"
              placeholder="Or type the item or need in plain words"
              placeholderTextColor={palette.muted}
              style={[styles.textarea, { color: palette.ink }]}
              accessibilityLabel="Request for the robot"
              editable={!locked}
              maxLength={MAX_LENGTH}
            />
            <Help>
              {request.length}/{MAX_LENGTH} · the robot only returns an item that
              is actually on a shelf
            </Help>
          </View>
        </NotchedSurface>

        {error || voice.error ? (
          <ErrorPanel
            title="That didn’t work"
            body={error ?? voice.error ?? undefined}
          />
        ) : null}

        {busy ? (
          <Card style={styles.thinking}>
            <ActivityIndicator color={palette.accent} />
            <View style={styles.thinkingText}>
              <Text style={[styles.thinkingTitle, { color: palette.ink }]}>
                Choosing the best item…
              </Text>
              <Help>Matching your request to what is on the shelves</Help>
            </View>
          </Card>
        ) : null}

        <AppButton
          label={busy ? "Choosing…" : "Ask Hampy"}
          onPress={submit}
          variant="ink"
          disabled={locked}
          chevrons={!busy}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

/** The ring that expands out of the mic while it is listening. */
function MicPulse({ color }: { color: string }) {
  const [progress] = useState(() => new Animated.Value(0));
  const [reduceMotion, setReduceMotion] = useState(true);

  useEffect(() => {
    let alive = true;
    void AccessibilityInfo.isReduceMotionEnabled().then((enabled) => {
      if (alive) setReduceMotion(enabled);
    });
    const subscription = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setReduceMotion,
    );
    return () => {
      alive = false;
      subscription.remove();
    };
  }, []);

  useEffect(() => {
    if (reduceMotion) return;
    const loop = Animated.loop(
      Animated.timing(progress, {
        toValue: 1,
        duration: 1600,
        easing: Easing.out(Easing.ease),
        useNativeDriver: true,
      }),
    );
    loop.start();
    return () => loop.stop();
  }, [progress, reduceMotion]);

  if (reduceMotion) return null;

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        styles.pulse,
        {
          opacity: progress.interpolate({
            inputRange: [0, 1],
            outputRange: [0.5, 0],
          }),
          transform: [
            {
              scale: progress.interpolate({
                inputRange: [0, 1],
                outputRange: [1, 1.4],
              }),
            },
          ],
        },
      ]}
    >
      <Hex size={MIC_SIZE} color="none" stroke={color} strokeWidth={2} />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  back: { flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 8 },
  backText: { fontSize: 14, fontWeight: "800" },
  askCard: { padding: 16, paddingTop: 26 },
  micWrap: { alignItems: "center", gap: 13, paddingBottom: 18 },
  micHit: { alignItems: "center", justifyContent: "center" },
  pulse: { alignItems: "center", justifyContent: "center" },
  micCaption: { fontSize: 16, fontWeight: "800" },
  micSub: {
    fontSize: 13.5,
    textAlign: "center",
    maxWidth: 260,
    lineHeight: 19,
  },
  recRow: { flexDirection: "row", alignItems: "center", gap: 7 },
  recDot: { width: 9, height: 9, borderRadius: 5 },
  recText: { fontSize: 14, fontWeight: "800" },
  inputBox: {
    borderWidth: 1,
    borderRadius: radius.field,
    padding: 14,
    gap: 8,
  },
  textarea: { minHeight: 84, fontSize: 16, lineHeight: 23, padding: 0 },
  thinking: { flexDirection: "row", alignItems: "center", gap: 12 },
  thinkingText: { flex: 1, minWidth: 0 },
  thinkingTitle: { fontSize: 15, fontWeight: "800" },
});
