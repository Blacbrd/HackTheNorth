import { useState, type ReactNode } from "react";
import {
  StyleSheet,
  View,
  type LayoutChangeEvent,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import Svg, { Path, Polygon } from "react-native-svg";
import { NOTCH, radius } from "@/theme/tokens";

/**
 * The two shapes this design is built from.
 *
 * React Native has no `clip-path`, so both are drawn as SVG behind normally
 * laid-out children rather than by clipping a box. The notch is a fixed number
 * of pixels, not a proportion, so its surface has to measure itself first —
 * a viewBox that scaled with the container would stretch the diagonal.
 */

/** Pointy-top hexagon: the badge shape for marks, the mic, and status icons. */
export function Hex({
  size,
  color,
  stroke,
  strokeWidth = 2,
  children,
  style,
}: {
  size: number;
  /** Pass "none" for an outline-only hexagon, as the mic's pulse ring does. */
  color: string;
  stroke?: string;
  strokeWidth?: number;
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const points = [
    [size * 0.5, 0],
    [size, size * 0.25],
    [size, size * 0.75],
    [size * 0.5, size],
    [0, size * 0.75],
    [0, size * 0.25],
  ]
    .map(([x, y]) => `${x},${y}`)
    .join(" ");

  return (
    <View style={[{ width: size, height: size }, styles.center, style]}>
      <Svg width={size} height={size} style={StyleSheet.absoluteFill}>
        <Polygon
          points={points}
          fill={color}
          stroke={stroke}
          strokeWidth={stroke ? strokeWidth : 0}
        />
      </Svg>
      {children}
    </View>
  );
}

/**
 * A panel with one corner cut off on the diagonal.
 *
 * `corner` picks which: "top-right" for the hero, the ask card and the camera,
 * "bottom-left" for the robot's target bar.
 */
export function NotchedSurface({
  children,
  color,
  borderColor,
  corner = "top-right",
  notch = NOTCH,
  cornerRadius = radius.card,
  style,
}: {
  children?: ReactNode;
  color: string;
  borderColor?: string;
  corner?: "top-right" | "bottom-left";
  notch?: number;
  /** Radius on the three corners that are not cut. 0 for the square heroes. */
  cornerRadius?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const [size, setSize] = useState<{ width: number; height: number } | null>(
    null,
  );
  const onLayout = (event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setSize((current) =>
      current?.width === width && current?.height === height
        ? current
        : { width, height },
    );
  };

  const path = size ? notchedPath(size, corner, notch, cornerRadius) : null;

  return (
    <View onLayout={onLayout} style={[styles.notched, style]}>
      {size && path ? (
        <Svg
          width={size.width}
          height={size.height}
          style={StyleSheet.absoluteFill}
          pointerEvents="none"
        >
          <Path
            d={path}
            fill={color}
            stroke={borderColor}
            strokeWidth={borderColor ? 1 : 0}
          />
        </Svg>
      ) : null}
      {children}
    </View>
  );
}

/** The panel outline: one corner cut on the diagonal, the other three rounded. */
function notchedPath(
  { width: w, height: h }: { width: number; height: number },
  corner: "top-right" | "bottom-left",
  notch: number,
  r: number,
): string {
  // Never let the radius or the notch outgrow the box it is cutting.
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  const n = Math.max(0, Math.min(notch, w - rr, h - rr));
  const arc = (x: number, y: number) => `A${rr} ${rr} 0 0 1 ${x} ${y}`;

  if (corner === "top-right") {
    return [
      `M${rr} 0`,
      `H${w - n}`,
      `L${w} ${n}`,
      `V${h - rr}`,
      arc(w - rr, h),
      `H${rr}`,
      arc(0, h - rr),
      `V${rr}`,
      arc(rr, 0),
      "Z",
    ].join(" ");
  }
  return [
    `M${rr} 0`,
    `H${w - rr}`,
    arc(w, rr),
    `V${h - rr}`,
    arc(w - rr, h),
    `H${n}`,
    `L0 ${h - n}`,
    `V${rr}`,
    arc(rr, 0),
    "Z",
  ].join(" ");
}

/**
 * The same corner cut, painted over content instead of behind it.
 *
 * `NotchedSurface` works by drawing the panel shape underneath its children,
 * which a full-bleed child like the camera's video would simply cover. This
 * masks the corner from above in the page background colour instead, so the
 * cut reads the same over an image.
 */
export function CornerNotch({
  size = NOTCH,
  color,
  corner = "top-right",
}: {
  size?: number;
  color: string;
  corner?: "top-right" | "bottom-left";
}) {
  const points =
    corner === "top-right"
      ? `0,0 ${size},0 ${size},${size}`
      : `0,0 ${size},${size} 0,${size}`;
  return (
    <View
      pointerEvents="none"
      style={[
        styles.cornerNotch,
        { width: size, height: size },
        corner === "top-right" ? { top: 0, right: 0 } : { bottom: 0, left: 0 },
      ]}
    >
      <Svg width={size} height={size}>
        <Polygon points={points} fill={color} />
      </Svg>
    </View>
  );
}

/** The fading triple chevron that trails a primary action. */
export function Chevrons({ color, size = 17 }: { color: string; size?: number }) {
  return (
    <View style={styles.chevrons}>
      {[1, 0.6, 0.3].map((opacity, index) => (
        <MaterialCommunityIcons
          key={opacity}
          name="chevron-right"
          size={size}
          color={color}
          style={{ opacity, marginLeft: index === 0 ? 0 : -size * 0.45 }}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: "center", justifyContent: "center" },
  notched: { backgroundColor: "transparent", overflow: "hidden" },
  cornerNotch: { position: "absolute", zIndex: 5 },
  chevrons: { flexDirection: "row", alignItems: "center" },
});
