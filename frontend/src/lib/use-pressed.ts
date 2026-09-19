import { useState } from "react";

/**
 * Press state as a plain boolean, for styling a `Pressable` from a style array.
 *
 * `Pressable` also accepts `style={({ pressed }) => ...}`, but NativeWind wraps
 * these components and that function form does not survive the wrapper on
 * native: the styles are dropped entirely, so a row loses `flexDirection` and a
 * button loses its fill. Array styles come through intact, so press state is
 * tracked here instead.
 */
export function usePressed() {
  const [pressed, setPressed] = useState(false);
  return {
    pressed,
    pressHandlers: {
      onPressIn: () => setPressed(true),
      onPressOut: () => setPressed(false),
    },
  };
}
