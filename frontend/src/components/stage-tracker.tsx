import { StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { radius, usePalette } from "@/theme/tokens";
import type { RobotFailure, RobotJob } from "@/types/api";

type Stage = { key: string; title: string; note: string };

export const STAGES: Stage[] = [
  { key: "queued", title: "Request received", note: "Robot is queuing the job" },
  { key: "driving", title: "Driving to the shelf", note: "On its way to shelf {n}" },
  { key: "picking", title: "Picking {item}", note: "Lining up and lifting the item" },
  { key: "returning", title: "Bringing it to you", note: "Heading back to the counter" },
  { key: "arrived", title: "Ready to collect", note: "At the counter — take {item}" },
];

/** Where a failure interrupts the run, so the tracker breaks at the right step. */
export function failureStageIndex(failure: RobotFailure): number {
  if (failure === "missing") return 2;
  if (failure === "blocked") return 1;
  return 3;
}

export function failureCopy(failure: RobotFailure) {
  if (failure === "missing")
    return {
      title: "That item was gone",
      sub: "Inventory was out of date",
      note: "Nothing matched at the pick point",
    };
  if (failure === "blocked")
    return {
      title: "The robot is stuck",
      sub: "Its path to the shelf is blocked",
      note: "Obstacle on the route to the shelf",
    };
  return {
    title: "The robot faulted",
    sub: "It stopped mid-run",
    note: "Motor fault reported",
  };
}

/**
 * Olive marks the ground already covered, mustard the step in progress, and
 * danger the step that broke — so the colour alone says how far the run got.
 */
export function StageTracker({ job }: { job: RobotJob }) {
  const palette = usePalette();
  const failAt = job.failure ? failureStageIndex(job.failure) : -1;
  const arrived = !job.failure && job.stage_index >= STAGES.length - 1;

  return (
    <View style={styles.track}>
      {STAGES.map((stage, index) => {
        const failedHere = failAt === index;
        const done = !failedHere && (index < job.stage_index || arrived);
        const active = !job.failure && !arrived && index === job.stage_index;
        const dim = !done && !active && !failedHere;

        const fill = failedHere
          ? palette.danger
          : done
            ? palette.olive
            : "transparent";
        const border = failedHere
          ? palette.danger
          : done
            ? palette.olive
            : active
              ? palette.mustard
              : palette.line;

        const text = stage.title
          .replace("{item}", job.item ?? "the item")
          .replace("{n}", String(job.shelf_number ?? "?"));
        const note = failedHere
          ? failureCopy(job.failure!).note
          : stage.note
              .replace("{item}", job.item ?? "the item")
              .replace("{n}", String(job.shelf_number ?? "?"));

        return (
          <View key={stage.key} style={styles.step}>
            <View style={styles.rail}>
              <View
                style={[
                  styles.dot,
                  { backgroundColor: fill, borderColor: border },
                ]}
              >
                {done ? (
                  <MaterialCommunityIcons
                    name="check"
                    size={14}
                    color={palette.onDark}
                  />
                ) : failedHere ? (
                  <MaterialCommunityIcons
                    name="close"
                    size={14}
                    color={palette.onDark}
                  />
                ) : active ? (
                  <View style={[styles.pip, { backgroundColor: palette.mustard }]} />
                ) : null}
              </View>
              {index < STAGES.length - 1 ? (
                <View
                  style={[
                    styles.bar,
                    { backgroundColor: done ? palette.olive : palette.line },
                  ]}
                />
              ) : null}
            </View>
            <View style={styles.label}>
              <Text
                style={[
                  styles.stepTitle,
                  {
                    color: failedHere
                      ? palette.danger
                      : dim
                        ? palette.muted
                        : palette.ink,
                  },
                ]}
              >
                {text}
              </Text>
              {active || failedHere ? (
                <Text style={[styles.stepNote, { color: palette.muted }]}>
                  {note}
                </Text>
              ) : null}
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  track: { marginTop: 4 },
  step: { flexDirection: "row", gap: 12, minHeight: 44 },
  rail: { alignItems: "center", width: 24 },
  dot: {
    width: 24,
    height: 24,
    borderRadius: radius.pill,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  pip: { width: 8, height: 8, borderRadius: 4 },
  bar: { width: 2, flex: 1, minHeight: 18 },
  label: { flex: 1, paddingBottom: 14 },
  stepTitle: { fontSize: 15, fontWeight: "800" },
  stepNote: { fontSize: 13, marginTop: 2 },
});
