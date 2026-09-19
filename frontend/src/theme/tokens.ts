import light from "./palette.json";
import { useTheme } from "./theme-context";

/**
 * Olive structure, mustard for the pop, one burnt-orange for the loud action,
 * on a warm cream base rather than white.
 *
 * Two roles keep contrast honest where one colour cannot serve both jobs:
 *
 * - `olive` is the *fill* under `onDark` text; `accent` is olive as *text and
 *   icons* on a light surface. Dark mode needs them to move in opposite
 *   directions — the fill goes darker so light text stays readable on it, the
 *   text colour goes lighter so it reads against the surface.
 * - `mustardInk` is mustard-family text on `bg`/`mustardSoft`; `onMustard` is
 *   text on a solid mustard fill, which needs to be markedly darker.
 */
const dark = {
  bg: "#15140D",
  surface: "#201E14",
  sand: "#2A2718",
  sandDeep: "#322E1C",

  olive: "#3E4A22",
  olivePressed: "#333D1C",
  oliveDeep: "#B7C77A",
  oliveTint: "#2E2C1A",
  accent: "#A8BA6B",

  mustard: "#E2B551",
  mustardSoft: "#3A3117",
  mustardInk: "#F0D9A0",
  onMustard: "#2A2310",

  orange: "#D96C39",
  orangePressed: "#BC5A2C",
  onOrange: "#1A1206",
  orangeTint: "#3A2A1C",

  ink: "#EEE8D5",
  inkPressed: "#D6D0BC",
  muted: "#A69E85",
  line: "#332F1F",
  onDark: "#F6F2E3",

  danger: "#E89079",
  dangerSoft: "#2B1B16",
  dangerLine: "#4A2C22",

  heroBg: "#2C3317",
  scrim: "rgba(0,0,0,0.58)",
  cameraBackground: "#0A0D06",
} as const;

export type Palette = typeof light;

/** The light palette, for the few places that cannot call a hook. */
export const colors = light;

export const radius = { card: 18, field: 12, pill: 999 } as const;
export const spacing = { page: 20, gap: 12, section: 24, touch: 48 } as const;

/** Size of the diagonal cut on notched surfaces. See `NotchedSurface`. */
export const NOTCH = 20;

export const type = {
  kicker: { fontSize: 11.5, fontWeight: "800", letterSpacing: 1.8 },
  title: { fontSize: 29, lineHeight: 32, fontWeight: "800", letterSpacing: -0.5 },
  section: { fontSize: 20, fontWeight: "800", letterSpacing: -0.2 },
  card: { fontSize: 16, fontWeight: "800" },
  body: { fontSize: 14.5, lineHeight: 20 },
  label: { fontSize: 13, fontWeight: "800" },
  help: { fontSize: 13, lineHeight: 18 },
} as const;

/** Content stays readable when the same code renders on tablet or web. */
export const MAX_CONTENT_WIDTH = 680;

/** The scheme comes from `ThemeProvider`, which the app sets rather than the OS. */
export function usePalette(): Palette {
  return useTheme().scheme === "dark" ? (dark as unknown as Palette) : light;
}

export function useIsDark(): boolean {
  return useTheme().scheme === "dark";
}
