/** @type {import('tailwindcss').Config} */
const palette = require("./src/theme/palette.json");

module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        canvas: palette.background,
        surface: palette.surface,
        "surface-muted": palette.surfaceMuted,
        action: palette.action,
        "action-pressed": palette.actionPressed,
        ink: palette.ink,
        muted: palette.muted,
        line: palette.line,
        danger: palette.danger,
        "danger-soft": palette.dangerSoft,
      },
      borderRadius: { card: "16px", field: "12px" },
    },
  },
};
