import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Image, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { apiUrl } from "@/services/api";
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
/**
 * The robot's forward-facing camera. `camera.left`/`camera.right` are the
 * wrist cameras looking down at the grippers, not a view of the room, so this
 * is the only topic worth showing a volunteer.
 */
const DEFAULT_TOPIC = "camera.head.jpeg";

/** Warm off-white and a muted sand, readable on the near-black camera fill. */
const ON_CAMERA = "#F3ECD6";
const ON_CAMERA_MUTED = "#C3BCA3";

type Status = "unavailable" | "connecting" | "live" | "stalled";

/**
 * Where frames come from.
 *
 * The proxy on our own backend is the default: the phone can always reach our
 * server, but the robot's own camera server sits on the robot's subnet, which
 * a phone on a different network (a hotspot, a different Wi-Fi) often cannot
 * reach directly. EXPO_PUBLIC_ROBOT_CAMERA_URL is an escape hatch for hitting
 * `camera_web.py` on the robot directly when the two do share a network.
 */
function defaultFrameUrl(topic: string): string {
  const override = process.env.EXPO_PUBLIC_ROBOT_CAMERA_URL;
  if (override) return `${override.replace(/\/$/, "")}/snapshot/${topic}.jpg`;
  return `${apiUrl}/api/robot/camera.jpg`;
}

/**
 * The robot's camera, viewed through our backend's proxy.
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
  baseUrl,
  topic = DEFAULT_TOPIC,
  maxFps = DEFAULT_MAX_FPS,
}: {
  shelfNumber: number | null;
  item: string | null;
  /** Full frame URL, sans cache-busting query. Defaults to our backend's
   *  camera proxy; see defaultFrameUrl for when that is overridden. */
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

  const status = feedStatus;
  const frameBase = baseUrl ?? defaultFrameUrl(topic);
  // The counter both defeats the image cache and identifies this frame.
  const loadingUri = `${frameBase}?f=${seq}`;
  const minInterval = Math.max(60, Math.round(1000 / Math.max(maxFps, 1)));

  const queueNext = (delay: number) => {
    if (pending.current) clearTimeout(pending.current);
    pending.current = setTimeout(() => setSeq((n) => n + 1), delay);
  };

  useEffect(() => {
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
  }, [frameBase]);

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
            styles.eye,
            status === "stalled" && styles.stalled,
          ]}
          accessibilityLabel="Robot camera feed"
        />
      ) : null}

      {/* The next frame, decoding out of sight. */}
      {status !== "unavailable" ? (
        <Image
          source={{ uri: loadingUri }}
          resizeMode="cover"
          style={[styles.eye, styles.buffering]}
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
            The backend can’t reach the robot’s camera. Check that
            camera_web.py is running on the robot.
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
  /**
   * `camera.head.jpeg` is a 2560x960 stereo pair — the two eyes side by side —
   * and showing it whole would put a seam down the middle of the picture. The
   * backend proxy already crops it to the left eye, which is 1280x960 and so
   * exactly the 4:3 of this frame; cropping there rather than here halves what
   * crosses the network, and the feed's rate is limited by bandwidth rather
   * than by the laptop's CPU.
   *
   * `cover` therefore fills the frame with no crop at all in the normal case,
   * and still degrades sensibly if the proxy ever passes a full pair through:
   * a centre crop, rather than a squashed one.
   */
  eye: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
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
