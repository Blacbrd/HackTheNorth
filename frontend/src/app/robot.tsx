import { ScrollView, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppButton } from "@/components/app-button";
import { RobotCamera } from "@/components/robot-camera";
import { Hex, NotchedSurface } from "@/components/shapes";
import { STAGES, StageTracker, failureCopy } from "@/components/stage-tracker";
import { EmptyState, Help, layout } from "@/components/ui";
import { useRobotJob } from "@/hooks/use-robot-job";
import { formatElapsed, titleCase } from "@/lib/items";
import { usePalette } from "@/theme/tokens";

export default function RobotScreen() {
  const palette = usePalette();
  const { job, recall, clear } = useRobotJob();

  if (!job || (!job.active && !job.failure && job.stage_index < 0)) {
    return (
      <SafeAreaView
        edges={["top", "left", "right"]}
        style={[layout.screen, { backgroundColor: palette.bg }]}
      >
        <View style={layout.page}>
          <EmptyState
            icon="robot-outline"
            title="The robot is idle"
            body="Ask for an item and its progress will appear here."
            action={
              <AppButton
                label="Ask Hampy"
                onPress={() => router.replace("/ask")}
                chevrons
                style={{ marginTop: 16, minWidth: 200 }}
              />
            }
          />
        </View>
      </SafeAreaView>
    );
  }

  const arrived = !job.failure && job.stage_index >= STAGES.length - 1;
  const failure = job.failure ? failureCopy(job.failure) : null;

  return (
    <SafeAreaView
      edges={["top", "left", "right"]}
      style={[layout.screen, { backgroundColor: palette.bg }]}
    >
      <ScrollView contentContainerStyle={layout.page}>
        <View style={styles.header} accessibilityLiveRegion="polite">
          <Hex size={52} color={failure ? palette.danger : palette.olive}>
            <MaterialCommunityIcons
              name={failure ? "alert-outline" : "robot-outline"}
              size={26}
              color={palette.onDark}
            />
          </Hex>
          <View style={styles.headerText}>
            <Text style={[styles.headerTitle, { color: palette.ink }]}>
              {failure
                ? failure.title
                : arrived
                  ? "Ready to collect"
                  : "Fetching your item"}
            </Text>
            <Help>
              {failure
                ? failure.sub
                : arrived
                  ? "The robot is at the counter"
                  : "Recall it any time below"}
            </Help>
          </View>
        </View>

        {/* The one fact that matters at a glance: what, and from where. */}
        <NotchedSurface
          color={palette.olive}
          corner="bottom-left"
          style={styles.target}
        >
          <View style={styles.targetTag}>
            <Text style={[styles.targetTagText, { color: palette.onDark }]}>
              SHELF {job.shelf_number ?? "—"}
            </Text>
          </View>
          <Text
            numberOfLines={1}
            style={[styles.targetItem, { color: palette.onDark }]}
          >
            {job.item ? titleCase(job.item) : "—"}
          </Text>
          {!failure && !arrived ? (
            <Text style={[styles.targetElapsed, { color: palette.onDark }]}>
              {formatElapsed(job.elapsed_seconds)}
            </Text>
          ) : null}
        </NotchedSurface>

        <RobotCamera shelfNumber={job.shelf_number} item={job.item} />

        <StageTracker job={job} />

        {failure ? (
          <View style={styles.actions}>
            {job.failure === "missing" ? (
              <>
                <AppButton
                  label="Ask for another item"
                  onPress={async () => {
                    await clear();
                    router.replace("/ask");
                  }}
                  icon={
                    <MaterialCommunityIcons
                      name="refresh"
                      size={20}
                      color={palette.onOrange}
                    />
                  }
                />
                <AppButton
                  label={`Open shelf ${job.shelf_number} to fix the count`}
                  variant="ghost"
                  onPress={async () => {
                    await clear();
                    router.replace("/");
                  }}
                />
              </>
            ) : (
              <AppButton
                label="Back to shelves"
                variant="ghost"
                onPress={async () => {
                  await clear();
                  router.replace("/");
                }}
              />
            )}
          </View>
        ) : arrived ? (
          <View style={styles.actions}>
            <View style={styles.collect}>
              <Hex size={58} color={palette.mustard}>
                <MaterialCommunityIcons
                  name="hand-back-right-outline"
                  size={28}
                  color={palette.onMustard}
                />
              </Hex>
              <Text style={[styles.collectTitle, { color: palette.ink }]}>
                Take {job.item} from the counter
              </Text>
              <Help>
                Then remove it from shelf {job.shelf_number} if the count should
                drop.
              </Help>
            </View>
            <AppButton
              label="Done — back to shelves"
              variant="olive"
              onPress={async () => {
                await clear();
                router.replace("/");
              }}
            />
          </View>
        ) : (
          <View style={styles.actions}>
            <AppButton
              label="Recall the robot"
              variant="danger"
              onPress={async () => {
                await recall();
                router.replace("/");
              }}
            />
            {job.simulated ? (
              <Text style={[styles.caveat, { color: palette.muted }]}>
                Stages advance on a server timer — the robot does not report its
                own progress yet, and recall only clears the job here.
              </Text>
            ) : null}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  headerText: { flex: 1, minWidth: 0 },
  headerTitle: { fontSize: 19, fontWeight: "800", letterSpacing: -0.2 },
  target: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 13,
  },
  targetTag: {
    backgroundColor: "rgba(255,255,255,0.18)",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  targetTagText: { fontSize: 12, fontWeight: "800", letterSpacing: 0.7 },
  targetItem: { flex: 1, fontSize: 18, fontWeight: "800" },
  targetElapsed: { fontSize: 13, fontWeight: "800", opacity: 0.85 },
  actions: { gap: 10 },
  collect: { alignItems: "center", gap: 8, paddingVertical: 8 },
  collectTitle: { fontSize: 16, fontWeight: "800", textAlign: "center" },
  caveat: { fontSize: 12, lineHeight: 17, textAlign: "center" },
});
