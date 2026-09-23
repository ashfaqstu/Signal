/**
 * Reads pixel values from rendered image URL using an offscreen canvas.
 */

import { ProbePixelData } from "../state/ui";

const canvasCache = new Map<string, ImageData>();

export async function readPixelFromUrl(
  url: string,
  x: number,
  y: number
): Promise<ProbePixelData | null> {
  if (x < 0 || y < 0) return null;

  let imageData = canvasCache.get(url);

  if (!imageData) {
    try {
      const img = new Image();
      img.crossOrigin = "anonymous";
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error("Failed to load image for probe"));
        img.src = url;
      });

      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return null;

      ctx.drawImage(img, 0, 0);
      imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      canvasCache.set(url, imageData);
    } catch {
      return null;
    }
  }

  const ix = Math.floor(x);
  const iy = Math.floor(y);

  if (ix >= imageData.width || iy >= imageData.height) {
    return null;
  }

  const idx = (iy * imageData.width + ix) * 4;
  const r = imageData.data[idx] / 255.0;
  const g = imageData.data[idx + 1] / 255.0;
  const b = imageData.data[idx + 2] / 255.0;

  const isRgb = Math.abs(r - g) > 0.01 || Math.abs(g - b) > 0.01;
  const gray = 0.299 * r + 0.587 * g + 0.114 * b;

  return {
    x: ix,
    y: iy,
    r,
    g,
    b,
    gray,
    isRgb,
  };
}
