/** @type {import('tailwindcss').Config} */
const palette = require("./src/theme/palette.json");

// Mirrors the light palette in src/theme/tokens.ts. Components style through
// `usePalette()` so they can follow the dark theme; these exist for the few
// places that reach for a utility class instead.
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        canvas: palette.bg,
        surface: palette.surface,
        sand: palette.sand,
        "sand-deep": palette.sandDeep,
        olive: palette.olive,
        "olive-pressed": palette.olivePressed,
        "olive-tint": palette.oliveTint,
        accent: palette.accent,
        mustard: palette.mustard,
        "mustard-soft": palette.mustardSoft,
        "mustard-ink": palette.mustardInk,
        orange: palette.orange,
        "orange-pressed": palette.orangePressed,
        ink: palette.ink,
        muted: palette.muted,
        line: palette.line,
        danger: palette.danger,
        "danger-soft": palette.dangerSoft,
      },
      borderRadius: { card: "18px", field: "12px" },
    },
  },
};
