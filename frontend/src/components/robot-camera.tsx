import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Image, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { radius, usePalette } from "@/theme/tokens";
import { CornerNotch } from "./shapes";

/** How long without a decoded frame before the feed counts as stalled. */
const STALL_MS = 6000;
/**
 * Ceiling on how often a frame is requested. The real rate settles lower on
 * its own, because the next request only goes out once the previous frame has
 * decoded — the link, not this number, is what limits throughput.
 */
const DEFAULT_MAX_FPS = 12;
/** Wait before retrying after a failed frame, so a dead link is not hammered. */
const RETRY_MS = 700;
/** The robot's forward-facing camera; `left`/`right` are the stereo pair. */
const DEFAULT_TOPIC = "camera.head.jpeg";

/** Warm off-white and a muted sand, readable on the near-black camera fill. */
const ON_CAMERA = "#F3ECD6";
const ON_CAMERA_MUTED = "#C3BCA3";

type Status = "unavailable" | "connecting" | "live" | "stalled";

/**
 * The robot's camera.
 *
 * `camera_web.py` serves single JPEGs from `/snapshot/<topic>.jpg` rather than
 * an MJPEG stream, so frames are polled. Two stacked images double-buffer
 * them: the next frame decodes underneath at zero opacity and is only promoted
 * once it has actually loaded. Swapping a single image's source instead leaves
 * a blank gap while each ~400KB frame decodes, which reads as flashing.
 *
 * Requests are paced off completions rather than a fixed timer. A timer faster
 * than the link builds a backlog of stale frames; waiting for each frame keeps
 * the feed at whatever rate the network genuinely sustains.
 *
 * A poll that never resolves looks exactly like a frozen feed, so a watchdog
 * treats silence as a stall. That is client-side guesswork, labelled as such.
 */
export function RobotCamera({
  shelfNumber,
  item,
  baseUrl = process.env.EXPO_PUBLIC_ROBOT_CAMERA_URL,
  topic = DEFAULT_TOPIC,
  maxFps = DEFAULT_MAX_FPS,
}: {
  shelfNumber: number | null;
  item: string | null;
  /** Origin of the robot's camera server, e.g. http://172.20.10.3:8082 */
  baseUrl?: string;
  topic?: string;
  maxFps?: number;
}) {
  const palette = usePalette();
  const [feedStatus, setFeedStatus] = useState<Status>("connecting");
  const [seq, setSeq] = useState(0);
  const [shownUri, setShownUri] = useState<string | null>(null);
  const lastFrame = useRef(0);
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Having no camera URL is not a state the feed transitions into — it is the
  // absence of a camera, so it is derived rather than stored.
  const status: Status = baseUrl ? feedStatus : "unavailable";
  const origin = baseUrl?.replace(/\/$/, "");
  // The counter both defeats the image cache and identifies this frame.
  const loadingUri = origin
    ? `${origin}/snapshot/${topic}.jpg?f=${seq}`
    : undefined;
  const minInterval = Math.max(60, Math.round(1000 / Math.max(maxFps, 1)));

  const queueNext = (delay: number) => {
    if (pending.current) clearTimeout(pending.current);
    pending.current = setTimeout(() => setSeq((n) => n + 1), delay);
  };

  useEffect(() => {
    if (!origin) return;
    lastFrame.current = Date.now();
    const watchdog = setInterval(() => {
      setFeedStatus((current) =>
        current !== "unavailable" && Date.now() - lastFrame.current > STALL_MS
          ? "stalled"
          : current,
      );
    }, 1500);
    return () => {
      clearInterval(watchdog);
      if (pending.current) clearTimeout(pending.current);
    };
  }, [origin]);

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
      {/* The frame currently on screen. It stays put while the next decodes. */}
      {shownUri && status !== "unavailable" ? (
        <Image
          source={{ uri: shownUri }}
          resizeMode="cover"
          style={[
            StyleSheet.absoluteFill,
            status === "stalled" && styles.stalled,
          ]}
          accessibilityLabel="Robot camera feed"
        />
      ) : null}

      {/* The next frame, decoding out of sight. */}
      {loadingUri && status !== "unavailable" ? (
        <Image
          source={{ uri: loadingUri }}
          resizeMode="cover"
          style={[StyleSheet.absoluteFill, styles.buffering]}
          onLoad={() => {
            lastFrame.current = Date.now();
            setFeedStatus("live");
            setShownUri(loadingUri);
            queueNext(minInterval);
          }}
          // One dropped frame is normal on a busy link; only the watchdog
          // decides the feed has actually gone away.
          onError={() => {
            if (Date.now() - lastFrame.current > STALL_MS) {
              setFeedStatus("unavailable");
            }
            queueNext(RETRY_MS);
          }}
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
            {baseUrl
              ? "No frames from the robot. It can still fetch the item."
              : "No camera configured. Set EXPO_PUBLIC_ROBOT_CAMERA_URL."}
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
  buffering: { opacity: 0 },
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
