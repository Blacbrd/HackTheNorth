import { Image, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { radius } from "@/theme/tokens";

export function RobotCamera({
  shelfNumber,
  item,
  streamUrl = process.env.EXPO_PUBLIC_ROBOT_CAMERA_URL,
}: {
  shelfNumber: number;
  item: string;
  streamUrl?: string;
}) {
  if (streamUrl)
    return (
      <View
        accessibilityLabel={`Robot camera feed. Target shelf ${shelfNumber}: ${item}.`}
        style={styles.camera}
      >
        <Image
          source={{ uri: streamUrl }}
          resizeMode="cover"
          style={StyleSheet.absoluteFill}
          accessibilityLabel="Robot camera feed"
        />
        <View style={styles.caption}>
          <Text style={styles.detail}>
            Target: shelf {shelfNumber} · {item}
          </Text>
        </View>
      </View>
    );
  return (
    <View
      accessibilityLabel={`Robot camera placeholder. Target shelf ${shelfNumber}: ${item}.`}
      style={styles.camera}
    >
      <MaterialCommunityIcons name="camera-outline" size={35} color="#FFFFFF" />
      <Text style={styles.title}>Camera will go here</Text>
      <Text style={styles.detail}>
        Target: shelf {shelfNumber} · {item}
      </Text>
    </View>
  );
}
const styles = StyleSheet.create({
  camera: {
    minHeight: 184,
    backgroundColor: "#101512",
    borderRadius: radius.card,
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    overflow: "hidden",
  },
  title: { color: "#FFFFFF", fontSize: 17, fontWeight: "700", marginTop: 10 },
  detail: { color: "#C9D3C9", fontSize: 14, marginTop: 4 },
  caption: {
    position: "absolute",
    left: 12,
    right: 12,
    bottom: 12,
    padding: 8,
    borderRadius: 8,
    backgroundColor: "rgba(0,0,0,0.7)",
  },
});
