import Constants from 'expo-constants';
import { File, Paths } from 'expo-file-system';
import { Platform } from 'react-native';

export type SimplifiedImage = { uri: string };

const API_PORT = 8000;

/**
 * Work out where the API is.
 *
 * `EXPO_PUBLIC_API_URL` wins when it is set. Otherwise fall back to whichever
 * host served the JS bundle: the device has already reached Metro at that
 * address, so the API running beside it on the same machine is reachable there
 * too. That keeps the app working on venue wifi, on a phone hotspot and in a
 * simulator without anyone editing an IP by hand.
 */
function resolveApiBase(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
  if (configured) return configured;

  const hostUri = Constants.expoConfig?.hostUri ?? Constants.expoGoConfig?.debuggerHost;
  const host = hostUri?.split('/')[0]?.split(':')[0];
  if (host) return `http://${host}:${API_PORT}`;

  return `http://localhost:${API_PORT}`;
}

export const apiBase = resolveApiBase();

/**
 * Turn a local photo URI into a real Blob for FormData.
 *
 * React Native 0.86 no longer accepts the duck-typed `{ uri, type, name }` part
 * and throws "Unsupported FormDataPart implementation" instead. On native,
 * expo-file-system's `File` implements Blob, so it can be appended directly.
 */
async function imagePart(uri: string, mimeType?: string | null): Promise<Blob> {
  if (Platform.OS === 'web') {
    return await (await fetch(uri)).blob();
  }

  const source = new File(uri);
  if (!source.exists) throw new Error('That photo is no longer on the device.');
  // The API rejects any part whose content type is not image/*, and File.type
  // comes back empty for an extension it cannot place, so fall back to the type
  // the camera or picker reported.
  if (source.type.startsWith('image/')) return source;
  return source.slice(0, source.size, mimeType ?? 'image/jpeg');
}

/** Prefer the API's own explanation over a generic apology. */
async function describeFailure(response: Response): Promise<string> {
  try {
    const detail = (await response.json())?.detail;
    if (typeof detail === 'string' && detail) return detail;
  } catch {
    // Not JSON; fall through to the generic message.
  }
  return `We could not simplify that photo (server said ${response.status}).`;
}

export async function simplifyImage(uri: string, mimeType?: string | null): Promise<SimplifiedImage> {
  const body = new FormData();
  body.append('image', await imagePart(uri, mimeType), 'source.jpg');

  let response: Response;
  try {
    response = await fetch(`${apiBase}/api/simplify`, { method: 'POST', body });
  } catch {
    // "Network request failed" on its own sends people hunting through the app,
    // when it nearly always means the phone cannot see the laptop.
    throw new Error(`Could not reach the server at ${apiBase}. Check it is running and that this device is on the same network.`);
  }

  if (!response.ok) {
    throw new Error(await describeFailure(response));
  }
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('image/png')) throw new Error('The server did not return a PNG drawing.');

  const imageBlob = await response.blob();
  if (Platform.OS === 'web') return { uri: URL.createObjectURL(imageBlob) };

  const drawing = new File(Paths.cache, 'current-drawing.png');
  drawing.create({ overwrite: true, intermediates: true });
  const imageBuffer = await imageBlob.arrayBuffer();
  drawing.write(new Uint8Array(imageBuffer));
  return { uri: drawing.uri };
}

export function disposeSimplifiedImage(uri: string): void {
  if (Platform.OS === 'web' && uri.startsWith('blob:')) URL.revokeObjectURL(uri);
}
