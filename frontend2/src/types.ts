export type Photo = {
  uri: string;
  mimeType?: string | null;
};

export type CameraPermission = {
  granted: boolean;
  canAskAgain: boolean;
};
