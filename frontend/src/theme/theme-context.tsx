import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Scheme = "light" | "dark";

type ThemeValue = {
  scheme: Scheme;
  toggle: () => void;
  setScheme: (next: Scheme) => void;
};

/**
 * The theme is chosen in the app, not taken from the device.
 *
 * `userInterfaceStyle` in app.json is native build-time config, which Expo Go
 * ignores — there `useColorScheme()` reports the OS setting, so a phone in dark
 * mode would drag the app with it whatever app.json says. Holding the choice
 * here makes it behave the same in Expo Go, a dev build and a store build.
 */
const ThemeContext = createContext<ThemeValue>({
  scheme: "light",
  toggle: () => {},
  setScheme: () => {},
});

export function ThemeProvider({
  children,
  initial = "light",
}: {
  children: ReactNode;
  initial?: Scheme;
}) {
  const [scheme, setScheme] = useState<Scheme>(initial);
  const toggle = useCallback(
    () => setScheme((current) => (current === "light" ? "dark" : "light")),
    [],
  );
  const value = useMemo(
    () => ({ scheme, toggle, setScheme }),
    [scheme, toggle],
  );
  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeValue {
  return useContext(ThemeContext);
}
