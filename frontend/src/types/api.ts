export type Shelf = { shelf_number: number; items: string[] };
export type ShelvesResponse = { shelves: Shelf[] };
export type Recommendation = {
  shelf_number: number;
  item: string;
  source: "app" | "robot";
};
