import { ColorSchemeName } from 'react-native';

export const palette = (scheme: ColorSchemeName) => scheme === 'dark'
  ? { background: '#111311', surface: '#1B1E1B', text: '#F7F8F5', muted: '#B7BDB6', line: '#343A34', accent: '#A8E063', onAccent: '#14200C', error: '#FFB4A9', camera: '#070907' }
  : { background: '#F6F7F3', surface: '#FFFFFF', text: '#172018', muted: '#657066', line: '#DCE0DA', accent: '#397A37', onAccent: '#FFFFFF', error: '#B3261E', camera: '#172018' };

export type AppColors = ReturnType<typeof palette>;

export const spacing = { x: 20, s: 12, l: 24, xl: 32 };
