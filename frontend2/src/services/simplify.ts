import { fetch as expoFetch } from 'expo/fetch';
import { File, Paths } from 'expo-file-system';
import { Platform } from 'react-native';

export type SimplifiedImage = { uri: string };

const apiBase = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000';

export async function simplifyImage(uri: string, mimeType?: string | null): Promise<SimplifiedImage> {
  const body = new FormData();
  const filename = mimeType === 'image/png' ? 'source.png' : 'source.jpg';
  const response = Platform.OS === 'web'
    ? await uploadFromWeb(uri, filename, body)
    : await uploadFromDevice(uri, filename, body);

  if (!response.ok) throw new Error('We could not simplify that photo. Please try again.');
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

async function uploadFromDevice(uri: string, filename: string, body: FormData) {
  const image = new File(uri);
  body.append('image', image, image.name || filename);
  return expoFetch(`${apiBase}/api/simplify`, { method: 'POST', body });
}

async function uploadFromWeb(uri: string, filename: string, body: FormData) {
  const source = await globalThis.fetch(uri);
  body.append('image', await source.blob(), filename);
  return globalThis.fetch(`${apiBase}/api/simplify`, { method: 'POST', body });
}
