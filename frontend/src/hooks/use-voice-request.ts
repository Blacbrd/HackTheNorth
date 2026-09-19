import { useRef, useState } from "react";
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from "expo-audio";
import { transcribeAudio } from "@/services/api";

export function useVoiceRequest(onTranscript: (text: string) => void) {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const transitionInProgress = useRef(false);
  const [status, setStatus] = useState<
    "idle" | "starting" | "recording" | "stopping" | "transcribing"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const toggle = async () => {
    if (transitionInProgress.current) return;
    transitionInProgress.current = true;
    setError(null);
    try {
      if (status === "idle") {
        setStatus("starting");
        const permission = await requestRecordingPermissionsAsync();
        if (!permission.granted)
          throw new Error(
            "Microphone access is needed to record a request. You can still type it instead.",
          );
        await setAudioModeAsync({
          allowsRecording: true,
          playsInSilentMode: true,
        });
        await recorder.prepareToRecordAsync();
        recorder.record();
        setStatus("recording");
        return;
      }
      if (status === "recording") {
        setStatus("stopping");
        await recorder.stop();
        const uri = recorder.uri;
        if (!uri) throw new Error("No audio was captured. Please try again.");
        setStatus("transcribing");
        onTranscript(await transcribeAudio(uri));
        setStatus("idle");
      }
    } catch (cause) {
      setStatus("idle");
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not turn that recording into text.",
      );
    } finally {
      transitionInProgress.current = false;
    }
  };
  return { status, error, toggle };
}
