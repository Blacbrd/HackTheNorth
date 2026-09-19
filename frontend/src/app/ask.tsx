import { useState } from "react";
import {
  ActivityIndicator,
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
import { RobotCamera } from "@/components/robot-camera";
import { useVoiceRequest } from "@/hooks/use-voice-request";
import { recommendationApi } from "@/services/api";
import type { Recommendation } from "@/types/api";
import { colors, radius } from "@/theme/tokens";

export default function AskScreen() {
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Recommendation | null>(null);
  const voice = useVoiceRequest((text) => setRequest(text));
  const submit = async () => {
    if (!request.trim()) {
      setError("Describe what you need so Hampy can choose an item.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await recommendationApi.ask(request.trim()));
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Hampy could not choose an item.",
      );
    } finally {
      setBusy(false);
    }
  };
  const listening = voice.status === "recording";
  const transcribing = voice.status === "transcribing";
  const changingRecording =
    voice.status === "starting" || voice.status === "stopping";
  return (
    <SafeAreaView className="flex-1 bg-canvas" style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back to shelves"
          onPress={() => router.back()}
          className="flex-row items-center"
          style={styles.back}
        >
          <MaterialCommunityIcons
            name="arrow-left"
            size={21}
            color={colors.action}
          />
          <Text className="text-action font-bold" style={styles.backText}>
            Shelves
          </Text>
        </Pressable>
        <View>
          <Text
            className="text-action text-xs font-extrabold tracking-widest"
            style={styles.kicker}
          >
            ASK HAMPY
          </Text>
          <Text
            className="text-ink text-3xl font-extrabold"
            style={styles.title}
          >
            What should the robot bring?
          </Text>
          <Text className="text-muted text-base" style={styles.subtitle}>
            Describe the need. Hampy checks the live shelves and selects an
            available match.
          </Text>
        </View>
        <View
          className="bg-surface border border-line rounded-card"
          style={styles.form}
        >
          <Text className="text-ink font-extrabold" style={styles.label}>
            Request
          </Text>
          <TextInput
            style={styles.textarea}
            value={request}
            onChangeText={setRequest}
            multiline
            textAlignVertical="top"
            placeholder="For example: I need a gluten-free dinner option…"
            placeholderTextColor={colors.muted}
            accessibilityLabel="Request for the robot"
            editable={!busy && !transcribing && !changingRecording}
            maxLength={700}
          />
          <View style={styles.formFooter}>
            <Text style={styles.help}>
              {transcribing
                ? "Transcribing your recording…"
                : changingRecording
                  ? "Preparing the microphone…"
                  : listening
                    ? "Recording — tap stop when you’re done."
                    : "Type a request or record one."}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={
                listening ? "Stop recording" : "Record a request"
              }
              onPress={voice.toggle}
              disabled={busy || transcribing || changingRecording}
              className={
                listening
                  ? "bg-danger rounded-full w-12 h-12 items-center justify-center active:scale-95 disabled:opacity-50"
                  : "bg-surface-muted rounded-full w-12 h-12 items-center justify-center active:scale-95 disabled:opacity-50"
              }
            >
              <MaterialCommunityIcons
                name={listening ? "stop" : "microphone-outline"}
                size={22}
                color={listening ? colors.surface : colors.action}
              />
            </Pressable>
          </View>
        </View>
        {(error || voice.error) && (
          <View
            accessibilityLiveRegion="polite"
            className="bg-danger-soft rounded-field flex-row"
            style={styles.error}
          >
            <MaterialCommunityIcons
              name="alert-circle-outline"
              size={19}
              color={colors.danger}
            />
            <Text style={styles.errorText}>{error ?? voice.error}</Text>
          </View>
        )}
        <AppButton
          label={busy ? "Choosing the Best Item…" : "Ask Hampy"}
          onPress={submit}
          disabled={busy || transcribing || changingRecording}
          icon={
            busy ? (
              <ActivityIndicator color={colors.surface} />
            ) : (
              <MaterialCommunityIcons
                name="robot-outline"
                size={20}
                color={colors.surface}
              />
            )
          }
        />
        {busy && (
          <View
            accessibilityLiveRegion="polite"
            className="bg-surface-muted rounded-card flex-row"
            style={styles.processing}
          >
            <View className="bg-surface rounded-full" style={styles.pulse}>
              <MaterialCommunityIcons
                name="robot-outline"
                size={26}
                color={colors.action}
              />
            </View>
            <View>
              <Text style={styles.processingTitle}>
                Choosing the best item…
              </Text>
              <Text style={styles.processingBody}>
                Checking dietary fit and what’s on the shelves.
              </Text>
            </View>
          </View>
        )}
        {result && (
          <View
            accessibilityLiveRegion="polite"
            className="bg-surface border border-line rounded-card"
            style={styles.result}
          >
            <View style={styles.resultHeading}>
              <View className="bg-action rounded-full" style={styles.check}>
                <MaterialCommunityIcons
                  name="check"
                  size={19}
                  color={colors.surface}
                />
              </View>
              <View style={styles.resultCopy}>
                <Text style={styles.resultKicker}>ROBOT TARGET READY</Text>
                <Text style={styles.resultTitle}>
                  Success! The robot will now retrieve the object.
                </Text>
                <Text style={styles.resultTarget}>
                  Shelf {result.shelf_number} · {result.item}
                </Text>
              </View>
            </View>
            <Text style={styles.resultBody}>
              Hampy sent this selection to the robot. Use the camera view below
              to follow its route.
            </Text>
            <RobotCamera shelfNumber={result.shelf_number} item={result.item} />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: {
    width: "100%",
    maxWidth: 680,
    alignSelf: "center",
    padding: 20,
    paddingBottom: 38,
    gap: 20,
  },
  back: {
    height: 48,
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingRight: 10,
  },
  backText: { color: colors.action, fontSize: 16, fontWeight: "700" },
  kicker: {
    color: colors.action,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1,
  },
  title: {
    color: colors.ink,
    fontSize: 30,
    lineHeight: 36,
    fontWeight: "800",
    marginTop: 5,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 16,
    lineHeight: 23,
    marginTop: 7,
    maxWidth: 540,
  },
  form: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.card,
    padding: 16,
  },
  label: {
    color: colors.ink,
    fontSize: 14,
    fontWeight: "800",
    marginBottom: 9,
  },
  textarea: {
    minHeight: 130,
    color: colors.ink,
    fontSize: 16,
    lineHeight: 23,
    padding: 0,
  },
  formFooter: {
    borderTopWidth: 1,
    borderTopColor: colors.line,
    marginTop: 12,
    paddingTop: 11,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  help: { color: colors.muted, flex: 1, fontSize: 13, lineHeight: 18 },
  error: {
    flexDirection: "row",
    gap: 8,
    padding: 12,
    backgroundColor: colors.dangerSoft,
    borderRadius: radius.field,
    alignItems: "flex-start",
  },
  errorText: { color: colors.danger, fontSize: 14, lineHeight: 20, flex: 1 },
  processing: {
    flexDirection: "row",
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.card,
    padding: 16,
    gap: 13,
    alignItems: "center",
  },
  pulse: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  processingTitle: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  processingBody: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
    marginTop: 2,
    flexShrink: 1,
  },
  result: {
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 14,
  },
  resultHeading: { flexDirection: "row", alignItems: "center", gap: 10 },
  resultCopy: { flex: 1, minWidth: 0 },
  check: {
    width: 38,
    height: 38,
    borderRadius: 19,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.action,
  },
  resultKicker: {
    color: colors.action,
    fontSize: 11,
    letterSpacing: 0.8,
    fontWeight: "800",
  },
  resultTitle: {
    color: colors.ink,
    fontSize: 18,
    fontWeight: "800",
    marginTop: 2,
  },
  resultTarget: {
    color: colors.action,
    fontSize: 14,
    fontWeight: "700",
    marginTop: 4,
  },
  resultBody: { color: colors.muted, fontSize: 14, lineHeight: 20 },
});
