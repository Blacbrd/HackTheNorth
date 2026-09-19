import { useCallback, useEffect, useRef, useState } from "react";
import { shelvesApi } from "@/services/api";
import type { Shelf } from "@/types/api";

export function useShelves() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const dataRevision = useRef(0);
  const refreshRequest = useRef(0);
  const refresh = useCallback(async () => {
    const request = ++refreshRequest.current;
    const revision = dataRevision.current;
    setLoading(true);
    setError(null);
    try {
      const nextShelves = await shelvesApi.list();
      if (
        request === refreshRequest.current &&
        revision === dataRevision.current
      ) {
        setShelves(nextShelves);
      }
    } catch (cause) {
      if (
        request === refreshRequest.current &&
        revision === dataRevision.current
      ) {
        setError(
          cause instanceof Error ? cause.message : "Could not load shelves.",
        );
      }
    } finally {
      if (request === refreshRequest.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      void refresh();
    }, 0);
    return () => clearTimeout(timer);
  }, [refresh]);
  const addItem = async (shelfNumber: number, item: string, quantity = 1) => {
    const shelf = await shelvesApi.addItem(shelfNumber, item, quantity);
    dataRevision.current += 1;
    setShelves((all) =>
      all.map((entry) => (entry.shelf_number === shelfNumber ? shelf : entry)),
    );
  };
  const removeItem = async (shelfNumber: number, item: string) => {
    const shelf = await shelvesApi.removeItem(shelfNumber, item);
    dataRevision.current += 1;
    setShelves((all) =>
      all.map((entry) => (entry.shelf_number === shelfNumber ? shelf : entry)),
    );
  };
  const addShelf = async () => {
    const shelf = await shelvesApi.create();
    dataRevision.current += 1;
    setShelves((all) =>
      [...all, shelf].sort((a, b) => a.shelf_number - b.shelf_number),
    );
    return shelf;
  };
  const removeShelf = async (shelfNumber: number) => {
    const remaining = await shelvesApi.remove(shelfNumber);
    dataRevision.current += 1;
    setShelves(remaining);
  };
  return {
    shelves,
    loading,
    error,
    refresh,
    addItem,
    removeItem,
    addShelf,
    removeShelf,
  };
}
