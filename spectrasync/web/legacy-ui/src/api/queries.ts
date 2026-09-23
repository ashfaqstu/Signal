import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "./client";
import {
  HealthResponse,
  MediaItem,
  PixelTimeseriesResponse,
  RegistriesResponse,
  RunResult,
  VideoFrameItem,
} from "./types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => request<HealthResponse>("/api/health"),
    staleTime: 30000,
  });
}

export function useRegistries() {
  return useQuery({
    queryKey: ["registries"],
    queryFn: () => request<RegistriesResponse>("/api/registries"),
    staleTime: Infinity,
  });
}

export function useMedia() {
  return useQuery({
    queryKey: ["media"],
    queryFn: () => request<MediaItem[]>("/api/media"),
    staleTime: 5000,
  });
}

export function useImportMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData();
      for (const f of files) {
        form.append("files", f);
      }
      const res = await fetch("/api/media", {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        throw new Error("Failed to upload media");
      }
      return res.json() as Promise<MediaItem[]>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media"] });
    },
  });
}

export function useDeleteMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mediaId: string) =>
      request<{ ok: boolean }>(`/api/media/${mediaId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media"] });
    },
  });
}

export function useVideoFrames(mediaId?: string, maxFrames: number = 24, step: number = 1) {
  return useQuery({
    queryKey: ["video-frames", mediaId, maxFrames, step],
    queryFn: () =>
      request<VideoFrameItem[]>(
        `/api/media/${mediaId}/frames?maxFrames=${maxFrames}&step=${step}`
      ),
    enabled: Boolean(mediaId),
    staleTime: 60000,
  });
}

export async function runWorkspace(
  workspace: string,
  params: Record<string, any>,
  signal?: AbortSignal
): Promise<RunResult> {
  return request<RunResult>(`/api/run/${workspace}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
    signal,
  });
}

export function usePixelTimeseries(
  runId: string | null,
  x: number | null,
  y: number | null,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ["pixel-timeseries", runId, x, y],
    queryFn: () =>
      request<PixelTimeseriesResponse>(
        `/api/runs/${runId}/pixel?x=${x}&y=${y}`
      ),
    enabled: Boolean(enabled && runId && x !== null && y !== null),
    staleTime: 60000,
  });
}
