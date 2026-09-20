export type Shelf = { shelf_number: number; items: string[] };
export type ShelvesResponse = { shelves: Shelf[] };

/** One item in a request, paired with the shelf it lives on. */
export type RobotJobItem = { shelf_number: number; item: string };

export type Recommendation = {
  items: RobotJobItem[];
  source: "app" | "robot";
  /** Mirrors items[0], kept for call sites that only care about one item. */
  shelf_number: number | null;
  item: string | null;
};

/**
 * One stage of a fetch. The server sends only one of two ordered lists for a
 * given job — single-item or two-item — never a mix of keys from both.
 */
export type RobotStage =
  | "picking"
  | "driving"
  | "arrived"
  | "queued"
  | "dropping_first"
  | "dropping_second";

export type RobotFailure = "missing" | "blocked" | "fault";

export type RobotJob = {
  active: boolean;
  stage: RobotStage | null;
  stage_index: number;
  /** The ordered stage keys for THIS job, as the server reports them. */
  stages: RobotStage[];
  shelf_number: number | null;
  item: string | null;
  /** Every item in the run; shelf_number/item above mirror items[0]. */
  items: RobotJobItem[];
  elapsed_seconds: number;
  failure: RobotFailure | null;
  /** Whether this run is fetching two items rather than one. */
  two_item: boolean;
  /** True when no real robot is attached — not whether stages are timed. */
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
