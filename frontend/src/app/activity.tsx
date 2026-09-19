import { useCallback, useEffect, useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Hex, NotchedSurface } from "@/components/shapes";
import {
  EmptyState,
  ErrorPanel,
  Kicker,
  SectionHeading,
  Sub,
  Title,
  layout,
} from "@/components/ui";
import { useRobotJob } from "@/hooks/use-robot-job";
import { timeAgo, titleCase } from "@/lib/items";
import { robotApi } from "@/services/api";
import { radius, usePalette } from "@/theme/tokens";
import type { HistoryEntry } from "@/types/api";

function loadErrorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Could not load activity.";
}

export default function ActivityScreen() {
  const palette = usePalette();
  const { job } = useRobotJob();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Pull-to-refresh, where the spinner is the point. */
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await robotApi.history());
      setError(null);
    } catch (cause) {
      setError(loadErrorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  // Refetch whenever the robot's job moves on, so the history stays in step
  // with it. The work is an async runner rather than a call out to `refresh`
  // so that nothing sets state synchronously as the effect runs, and so a
  // reply that lands after unmount is dropped instead of setting state.
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const next = await robotApi.history();
        if (cancelled) return;
        setEntries(next);
        setError(null);
      } catch (cause) {
        if (!cancelled) setError(loadErrorMessage(cause));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [job?.stage_index, job?.failure]);

  const busy = Boolean(job?.active || job?.failure);

  return (
    <SafeAreaView
      edges={["top", "left", "right"]}
      style={[layout.screen, { backgroundColor: palette.bg }]}
    >
      <ScrollView
        contentContainerStyle={layout.page}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={palette.accent}
          />
        }
      >
        <View>
          <Kicker>Hampy · Activity</Kicker>
          <Title>Requests &amp; robot</Title>
          <Sub>What you have asked for, and what the robot is doing now.</Sub>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={busy ? "Open robot progress" : "The robot is idle"}
          disabled={!busy}
          onPress={() => router.push("/robot")}
        >
          <NotchedSurface
            color={palette.heroBg}
            cornerRadius={0}
            style={styles.status}
          >
            <Hex size={52} color={job?.failure ? palette.danger : palette.mustard}>
              <MaterialCommunityIcons
                name={job?.failure ? "alert-outline" : "robot-outline"}
                size={26}
                color={job?.failure ? palette.onDark : palette.onMustard}
              />
            </Hex>
            <View style={styles.statusText}>
              <Text style={[styles.statusTitle, { color: palette.onDark }]}>
                {job?.failure
                  ? "The robot needs you"
                  : job?.active
                    ? "Fetching an item"
                    : "Robot is idle"}
              </Text>
              <Text style={[styles.statusSub, { color: palette.onDark }]}>
                {job?.item
                  ? `${titleCase(job.item)} · shelf ${job.shelf_number}`
                  : "At the counter, ready for the next request."}
              </Text>
            </View>
            {busy ? (
              <MaterialCommunityIcons
                name="chevron-right"
                size={22}
                color={palette.onDark}
              />
            ) : null}
          </NotchedSurface>
        </Pressable>

        {error ? <ErrorPanel title="Couldn’t load activity" body={error} /> : null}

        <SectionHeading>Recent requests</SectionHeading>

        {!entries.length && !loading ? (
          <EmptyState
            icon="history"
            title="Nothing asked yet"
            body="Requests you make will be listed here with what the robot fetched."
          />
        ) : (
          <View style={styles.list}>
            {entries.map((entry) => (
              <View
                key={entry.id}
                style={[
                  styles.row,
                  { backgroundColor: palette.surface, borderColor: palette.line },
                ]}
              >
                <View
                  style={[
                    styles.rowIcon,
                    {
                      backgroundColor: entry.succeeded
                        ? palette.oliveTint
                        : palette.dangerSoft,
                    },
                  ]}
                >
                  <MaterialCommunityIcons
                    name={entry.succeeded ? "check" : "alert-outline"}
                    size={20}
                    color={entry.succeeded ? palette.accent : palette.danger}
                  />
                </View>
                <View style={styles.rowText}>
                  <Text style={[styles.rowTitle, { color: palette.ink }]}>
                    {entry.succeeded && entry.item
                      ? titleCase(entry.item)
                      : "No item fetched"}
                  </Text>
                  <Text
                    style={[styles.rowBody, { color: palette.muted }]}
                    numberOfLines={2}
                  >
                    “{entry.user_input}”
                    {entry.succeeded
                      ? ` · shelf ${entry.shelf_number}`
                      : entry.failure
                        ? ` · ${entry.failure}`
                        : ""}
                  </Text>
                </View>
                <Text style={[styles.rowWhen, { color: palette.muted }]}>
                  {timeAgo(entry.created_at)}
                </Text>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  status: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    padding: 16,
  },
  statusText: { flex: 1, minWidth: 0 },
  statusTitle: { fontSize: 18, fontWeight: "800", letterSpacing: -0.2 },
  statusSub: { fontSize: 13.5, lineHeight: 18, marginTop: 2, opacity: 0.85 },
  list: { gap: 10 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: radius.field,
    padding: 13,
  },
  rowIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  rowText: { flex: 1, minWidth: 0 },
  rowTitle: { fontSize: 15, fontWeight: "800" },
  rowBody: { fontSize: 13, marginTop: 1, lineHeight: 18 },
  rowWhen: { fontSize: 12 },
});
