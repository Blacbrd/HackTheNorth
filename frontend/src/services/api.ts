import { Platform } from "react-native";
import type { Recommendation, Shelf, ShelvesResponse } from "@/types/api";

const apiUrl = (
  process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, init);
  } catch {
    throw new Error(
      "Cannot reach the API. Check the server address and connection.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail || `Request failed (${response.status}). Try again.`,
    );
  }
  return response.json() as Promise<T>;
}

export const shelvesApi = {
  list: async () => (await request<ShelvesResponse>("/api/shelves")).shelves,
  addItem: (shelfNumber: number, item: string) =>
    request<Shelf>(`/api/shelves/${shelfNumber}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item }),
    }),
  removeItem: (shelfNumber: number, item: string) =>
    request<Shelf>(
      `/api/shelves/${shelfNumber}/items/${encodeURIComponent(item)}`,
      { method: "DELETE" },
    ),
};

export const recommendationApi = {
  ask: (userInput: string) =>
    request<Recommendation>("/api/recommendations/app", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: userInput }),
    }),
};

export async function transcribeAudio(uri: string): Promise<string> {
  let extension =
    uri.match(/\.([a-z0-9]+)(?:\?|$)/i)?.[1]?.toLowerCase() ?? "m4a";
  let mime =
    extension === "webm"
      ? "audio/webm"
      : extension === "wav"
        ? "audio/wav"
        : extension === "ogg"
          ? "audio/ogg"
          : extension === "mp3"
            ? "audio/mpeg"
            : "audio/m4a";
  const form = new FormData();
  if (Platform.OS === "web") {
    const audio = await fetch(uri).then((response) => response.blob());
    if (audio.size > 10 * 1024 * 1024)
      throw new Error(
        "That recording is too large. Keep it under 10 MB and try again.",
      );
    mime = audio.type || mime;
    if (!uri.match(/\.([a-z0-9]+)(?:\?|$)/i))
      extension = mime.includes("webm")
        ? "webm"
        : mime.includes("wav")
          ? "wav"
          : mime.includes("ogg")
            ? "ogg"
            : mime.includes("mpeg")
              ? "mp3"
              : "m4a";
    form.append(
      "audio",
      new File([audio], `request.${extension}`, { type: mime }),
    );
  } else {
    form.append("audio", {
      uri,
      name: `request.${extension}`,
      type: mime,
    } as unknown as Blob);
  }
  const result = await request<{ text: string }>("/api/transcriptions", {
    method: "POST",
    body: form,
  });
  return result.text;
}
