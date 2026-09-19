import { File, Paths } from 'expo-file-system';
import { Platform } from 'react-native';

export type SimplifiedImage = { uri: string };

const apiBase = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000';

export async function simplifyImage(uri: string, mimeType?: string | null): Promise<SimplifiedImage> {
  const body = new FormData();
  body.append('image', { uri, type: mimeType ?? 'image/jpeg', name: 'source.jpg' } as unknown as Blob);
  const response = await fetch(`${apiBase}/api/simplify`, { method: 'POST', body });
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
