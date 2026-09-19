export type Shelf = { shelf_number: number; items: string[] };
export type ShelvesResponse = { shelves: Shelf[] };
export type Recommendation = {
  shelf_number: number;
  item: string;
  source: "app" | "robot";
};

/** One stage of a fetch, in the order the robot works through them. */
export type RobotStage =
  | "queued"
  | "driving"
  | "picking"
  | "returning"
  | "arrived";

export type RobotFailure = "missing" | "blocked" | "fault";

export type RobotJob = {
  active: boolean;
  stage: RobotStage | null;
  stage_index: number;
  shelf_number: number | null;
  item: string | null;
  elapsed_seconds: number;
  failure: RobotFailure | null;
  /** True while stages advance on a server timer rather than robot telemetry. */
  simulated: boolean;
};

export type HistoryEntry = {
  id: string;
  user_input: string;
  item: string | null;
  shelf_number: number | null;
  succeeded: boolean;
  failure: RobotFailure | null;
  created_at: string;
};

export type HistoryResponse = { entries: HistoryEntry[] };

/** One item name on a shelf, with how many of it are there. */
export type GroupedItem = { name: string; count: number };

/** A search match: an item, how many, and which shelf holds it. */
export type ItemHit = GroupedItem & { shelfNumber: number };
