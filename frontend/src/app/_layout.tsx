import "@/global.css";
import { StyleSheet, View, type ColorValue } from "react-native";
import { Tabs } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "@/theme/theme-context";
import { radius, useIsDark, usePalette, type Palette } from "@/theme/tokens";

/**
 * The active tab is the one place orange appears outside a primary button:
 * it sits in a soft orange lozenge so the current tab reads at a glance
 * without another loud fill competing with the hero.
 */
function TabIcon({
  name,
  color,
  focused,
  palette,
}: {
  name: keyof typeof MaterialCommunityIcons.glyphMap;
  color: ColorValue;
  focused: boolean;
  palette: Palette;
}) {
  return (
    <View
      style={[
        styles.tabIcon,
        focused && { backgroundColor: palette.orangeTint },
      ]}
    >
      <MaterialCommunityIcons name={name} size={22} color={color as string} />
    </View>
  );
}

export default function RootLayout() {
  return (
    <ThemeProvider>
      <AppTabs />
    </ThemeProvider>
  );
}

function AppTabs() {
  const palette = usePalette();
  const dark = useIsDark();

  return (
    <SafeAreaProvider>
      <StatusBar style={dark ? "light" : "dark"} />
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: palette.orange,
          tabBarInactiveTintColor: palette.muted,
          tabBarStyle: {
            backgroundColor: palette.surface,
            borderTopColor: palette.line,
            height: 64,
            paddingTop: 6,
          },
          tabBarLabelStyle: { fontSize: 11, fontWeight: "800" },
          tabBarItemStyle: { paddingVertical: 2 },
          sceneStyle: { backgroundColor: palette.bg },
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: "Shelves",
            tabBarIcon: ({ color, focused }) => (
              <TabIcon
                name="package-variant-closed"
                color={color}
                focused={focused}
                palette={palette}
              />
            ),
          }}
        />
        <Tabs.Screen
          name="ask"
          options={{
            title: "Ask",
            tabBarIcon: ({ color, focused }) => (
              <TabIcon
                name="robot-outline"
                color={color}
                focused={focused}
                palette={palette}
              />
            ),
          }}
        />
        <Tabs.Screen
          name="activity"
          options={{
            title: "Activity",
            tabBarIcon: ({ color, focused }) => (
              <TabIcon
                name="history"
                color={color}
                focused={focused}
                palette={palette}
              />
            ),
          }}
        />
        {/* Reached from Ask and Activity, never a tab of its own. */}
        <Tabs.Screen name="robot" options={{ href: null }} />
      </Tabs>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  tabIcon: {
    width: 52,
    height: 30,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },
});
