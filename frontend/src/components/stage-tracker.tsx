import { StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { radius, usePalette } from "@/theme/tokens";
import type { RobotFailure, RobotJob, RobotStage } from "@/types/api";

/** Falls back to when the server predates `stages` or hasn't started the job. */
const DEFAULT_STAGES: RobotStage[] = ["picking", "driving", "arrived"];

/** Copy for every stage key across both lists the server can send. */
const STAGE_COPY: Record<RobotStage, { title: string; note: string }> = {
  picking: { title: "Initial pick up", note: "Picking {item} up off the shelf" },
  driving: { title: "Driving to shelf", note: "Carrying {item} to the drop-off" },
  queued: { title: "Request received", note: "The robot is starting the job" },
  dropping_first: {
    title: "Dropping off first item",
    note: "Taking the first item to its shelf",
  },
  dropping_second: {
    title: "Dropping off second item",
    note: "Taking the second item to its shelf",
  },
  arrived: { title: "Ready to collect", note: "Take {item} from the counter" },
};

/**
 * The stage list for this job. The server sends exactly the keys the job will
 * go through, but an older backend or a job that hasn't started yet can send
 * an empty array — fall back to the single-item list so the tracker always
 * has something to render.
 */
export function stageList(job: RobotJob): RobotStage[] {
  return job.stages.length > 0 ? job.stages : DEFAULT_STAGES;
}

/** Whether the run has reached its last stage cleanly. */
export function isArrived(job: RobotJob): boolean {
  return !job.failure && job.stage_index >= stageList(job).length - 1;
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
  const stages = stageList(job);
  const arrived = isArrived(job);

  return (
    <View style={styles.track}>
      {stages.map((key, index) => {
        const stage = STAGE_COPY[key];
        // The server now reports a failure at the stage it actually happened
        // in, so the failed step is just wherever stage_index points.
        const failedHere = Boolean(job.failure) && index === job.stage_index;
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
          <View key={key} style={styles.step}>
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
              {index < stages.length - 1 ? (
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
