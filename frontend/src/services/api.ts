import Constants from "expo-constants";
// Aliased: the web branch below builds a DOM File, which this would shadow.
import { File as FileSystemFile, UploadType } from "expo-file-system";
import { Platform } from "react-native";
import type {
  HistoryEntry,
  HistoryResponse,
  Recommendation,
  RobotFailure,
  RobotJob,
  Shelf,
  ShelvesResponse,
} from "@/types/api";

const API_PORT = process.env.EXPO_PUBLIC_API_PORT ?? "8000";
const MAX_AUDIO_BYTES = 10 * 1024 * 1024;

/**
 * Work out where the API is.
 *
 * `EXPO_PUBLIC_API_URL` wins when set. Otherwise fall back to whichever host
 * served the JS bundle: the device already reached Metro at that address, so
 * the API beside it on the same machine is reachable there too. A phone can
 * never resolve the loopback default on its own.
 */
function resolveApiUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "");
  if (configured) return configured;

  const hostUri =
    Constants.expoConfig?.hostUri ?? Constants.expoGoConfig?.debuggerHost;
  const host = hostUri?.split("/")[0]?.split(":")[0];
  if (host) return `http://${host}:${API_PORT}`;

  return `http://127.0.0.1:${API_PORT}`;
}

export const apiUrl = resolveApiUrl();

function apiCandidates(): string[] {
  const candidates = [apiUrl];
  if (Platform.OS === "web" && globalThis.location?.hostname === "localhost") {
    candidates.push(`http://127.0.0.1:${API_PORT}`);
  }
  return Array.from(new Set(candidates));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  let lastUrl = apiUrl;
  for (const baseUrl of apiCandidates()) {
    lastUrl = baseUrl;
    try {
      response = await fetch(`${baseUrl}${path}`, init);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          body.detail || `Request failed (${response.status}). Try again.`,
        );
      }
      return response.json() as Promise<T>;
    } catch (error) {
      if (baseUrl === apiCandidates().at(-1)) {
        if (error instanceof Error && !error.message.includes("Failed to fetch")) {
          throw error;
        }
        break;
      }
    }
  }
  throw new Error(
    `Cannot reach the API at ${lastUrl}. Check the server is running and that this device is on the same network.`,
  );
}

export const shelvesApi = {
  list: async () => (await request<ShelvesResponse>("/api/shelves")).shelves,
  /** Without a number the server appends the next one after the highest in use. */
  create: (shelfNumber?: number) =>
    request<Shelf>("/api/shelves", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shelf_number: shelfNumber ?? null }),
    }),
  /** Resolves to the shelves that remain, so the list redraws in one trip. */
  remove: async (shelfNumber: number) =>
    (await request<ShelvesResponse>(`/api/shelves/${shelfNumber}`, {
      method: "DELETE",
    })).shelves,
  /** Adds `quantity` copies in one request; a shelf stores count as repetition. */
  addItem: (shelfNumber: number, item: string, quantity = 1) =>
    request<Shelf>(`/api/shelves/${shelfNumber}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item, quantity }),
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

export const robotApi = {
  job: () => request<RobotJob>("/api/robot/job"),
  recall: () => request<RobotJob>("/api/robot/job/recall", { method: "POST" }),
  clear: () => request<RobotJob>("/api/robot/job/clear", { method: "POST" }),
  /** Forces a failure so those states can be exercised without a real obstacle. */
  fail: (failure: RobotFailure) =>
    request<RobotJob>(`/api/robot/job/fail/${failure}`, { method: "POST" }),
  history: async (): Promise<HistoryEntry[]> =>
    (await request<HistoryResponse>("/api/robot/history")).entries,
  cameraStatus: () =>
    request<{ available: boolean; url: string }>("/api/robot/camera/status"),
};

/** The API only accepts a fixed set of audio MIME types, so derive one from
 *  the recording's extension rather than trusting whatever the OS reports. */
function audioMimeFor(extension: string): string {
  switch (extension) {
    case "webm":
      return "audio/webm";
    case "wav":
      return "audio/wav";
    case "ogg":
      return "audio/ogg";
    case "mp3":
      return "audio/mpeg";
    default:
      return "audio/m4a";
  }
}

function extensionForMime(mime: string): string {
  if (mime.includes("webm")) return "webm";
  if (mime.includes("wav")) return "wav";
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("mpeg")) return "mp3";
  return "m4a";
}

const TOO_LARGE = "That recording is too large. Keep it under 10 MB and try again.";

function unreachable(): Error {
  return new Error(
    `Cannot reach the API at ${apiUrl}. Check the server is running and that this device is on the same network.`,
  );
}

export async function transcribeAudio(uri: string): Promise<string> {
  const extension =
    uri.match(/\.([a-z0-9]+)(?:\?|$)/i)?.[1]?.toLowerCase() ?? "m4a";

  if (Platform.OS === "web") {
    const audio = await fetch(uri).then((response) => response.blob());
    if (audio.size > MAX_AUDIO_BYTES) throw new Error(TOO_LARGE);
    const mime = audio.type || audioMimeFor(extension);
    const name = `request.${uri.match(/\.([a-z0-9]+)(?:\?|$)/i) ? extension : extensionForMime(mime)}`;
    const form = new FormData();
    form.append("audio", new File([audio], name, { type: mime }));
    const result = await request<{ text: string }>("/api/transcriptions", {
      method: "POST",
      body: form,
    });
    return result.text;
  }

  const recording = new FileSystemFile(uri);
  if (!recording.exists)
    throw new Error("That recording is no longer on the device.");
  if (recording.size > MAX_AUDIO_BYTES) throw new Error(TOO_LARGE);

  // Hand the file straight to the native uploader instead of assembling the
  // multipart body in JS. React Native's Blob cannot be built from the file's
  // bytes — slicing it throws "Creating blobs from ArrayBuffer and
  // ArrayBufferView are not supported" — and the older
  // `{ uri, name, type }` FormData part is rejected as an unsupported
  // FormDataPart implementation. The native path sidesteps both.
  let response;
  try {
    response = await recording.upload(`${apiUrl}/api/transcriptions`, {
      httpMethod: "POST",
      uploadType: UploadType.MULTIPART,
      fieldName: "audio",
      mimeType: audioMimeFor(extension),
    });
  } catch {
    throw unreachable();
  }

  let body: { text?: string; detail?: string } = {};
  try {
    body = JSON.parse(response.body);
  } catch {
    // Leave it empty; the status check below produces the message.
  }
  if (response.status < 200 || response.status >= 300)
    throw new Error(
      body.detail || `Request failed (${response.status}). Try again.`,
    );
  if (!body.text)
    throw new Error("The server returned no transcription. Please try again.");
  return body.text;
}
