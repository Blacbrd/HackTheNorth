import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Image, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { radius, usePalette } from "@/theme/tokens";
import { CornerNotch } from "./shapes";

/** How long without a decoded frame before the feed counts as stalled. */
const STALL_MS = 6000;

/** Warm off-white and a muted sand, readable on the near-black camera fill. */
const ON_CAMERA = "#F3ECD6";
const ON_CAMERA_MUTED = "#C3BCA3";

type Status = "unavailable" | "connecting" | "live" | "stalled";

/**
 * The robot's camera.
 *
 * The stream is MJPEG, which React Native renders as a never-finishing Image.
 * That means there is no "it broke" event to listen for — onLoad fires once and
 * a frozen feed looks identical to a live one. So a watchdog treats silence as
 * a stall, which is client-side guesswork and labelled as such.
 */
export function RobotCamera({
  shelfNumber,
  item,
  streamUrl = process.env.EXPO_PUBLIC_ROBOT_CAMERA_URL,
}: {
  shelfNumber: number | null;
  item: string | null;
  streamUrl?: string;
}) {
  const palette = usePalette();
  const [feedStatus, setFeedStatus] = useState<Status>("connecting");
  // Stamped by the effect below before the watchdog first reads it.
  const lastFrame = useRef(0);

  // Having no stream URL is not a state the feed transitions into — it is the
  // absence of a camera, so it is derived rather than stored.
  const status: Status = streamUrl ? feedStatus : "unavailable";

  useEffect(() => {
    if (!streamUrl) return;
    lastFrame.current = Date.now();
    const watchdog = setInterval(() => {
      setFeedStatus((current) =>
        current !== "unavailable" && Date.now() - lastFrame.current > STALL_MS
          ? "stalled"
          : current,
      );
    }, 1500);
    return () => clearInterval(watchdog);
  }, [streamUrl]);

  const caption =
    shelfNumber !== null && item
      ? `Target: shelf ${shelfNumber} · ${item}`
      : "No target";

  return (
    <View
      accessibilityLabel={`Robot camera, ${status}. ${caption}`}
      style={[
        styles.frame,
        { backgroundColor: palette.cameraBackground, borderColor: palette.line },
      ]}
    >
      {streamUrl && status !== "unavailable" ? (
        <Image
          source={{ uri: streamUrl }}
          resizeMode="cover"
          style={[
            StyleSheet.absoluteFill,
            status === "stalled" && styles.stalled,
          ]}
          onLoadStart={() => {
            lastFrame.current = Date.now();
          }}
          onLoad={() => {
            lastFrame.current = Date.now();
            setFeedStatus("live");
          }}
          onError={() => setFeedStatus("unavailable")}
          accessibilityLabel="Robot camera feed"
        />
      ) : null}

      {status === "connecting" ? (
        <View style={styles.message}>
          <ActivityIndicator color={ON_CAMERA} />
          <Text style={styles.messageTitle}>Connecting to camera…</Text>
          <Text style={styles.messageBody}>Waiting for the first frame</Text>
        </View>
      ) : null}

      {status === "unavailable" ? (
        <View style={styles.message}>
          <MaterialCommunityIcons
            name="camera-off-outline"
            size={28}
            color={ON_CAMERA}
          />
          <Text style={styles.messageTitle}>Camera offline</Text>
          <Text style={styles.messageBody}>
            No video from the robot. It can still fetch the item.
          </Text>
        </View>
      ) : null}

      {status === "live" ? (
        <View style={[styles.tag, styles.tagLive]}>
          <View style={[styles.liveDot, { backgroundColor: palette.orange }]} />
          <Text style={styles.tagText}>LIVE</Text>
        </View>
      ) : null}

      {status === "stalled" ? (
        <>
          <View style={[styles.tag, styles.tagStalled]}>
            <Text style={styles.tagText}>SIGNAL STALLED</Text>
          </View>
          <View style={styles.message}>
            <Text style={styles.messageTitle}>Video stalled</Text>
            <Text style={styles.messageBody}>
              Last frame is frozen — the robot may still be working
            </Text>
          </View>
        </>
      ) : null}

      <View style={styles.caption}>
        <Text style={styles.captionText}>{caption}</Text>
      </View>

      <CornerNotch color={palette.bg} />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    aspectRatio: 4 / 3,
    borderRadius: radius.card,
    borderWidth: 1,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
  },
  stalled: { opacity: 0.55 },
  message: { alignItems: "center", padding: 20, gap: 6 },
  messageTitle: { color: ON_CAMERA, fontSize: 15, fontWeight: "800" },
  messageBody: {
    color: ON_CAMERA_MUTED,
    fontSize: 13,
    textAlign: "center",
    lineHeight: 18,
  },
  tag: {
    position: "absolute",
    top: 10,
    left: 10,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  tagLive: { backgroundColor: "rgba(0,0,0,0.5)" },
  tagStalled: { backgroundColor: "rgba(120,70,20,0.75)" },
  tagText: {
    color: ON_CAMERA,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
  },
  liveDot: { width: 8, height: 8, borderRadius: 4 },
  caption: {
    position: "absolute",
    left: 12,
    right: 12,
    bottom: 12,
    padding: 8,
    borderRadius: 8,
    backgroundColor: "rgba(0,0,0,0.7)",
  },
  captionText: { color: ON_CAMERA_MUTED, fontSize: 13 },
});
