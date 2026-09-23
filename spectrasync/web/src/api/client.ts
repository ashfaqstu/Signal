/**
 * API Fetch Client with typed errors.
 */

import { ApiErrorPayload } from "./types";

export class ApiError extends Error {
  code: string;
  status: number;
  data?: any;

  constructor(status: number, payload: ApiErrorPayload | string) {
    if (typeof payload === "object" && payload !== null) {
      super(payload.message || payload.code || "API Error");
      this.code = payload.code || "unknown_error";
      this.data = payload;
    } else {
      super(String(payload));
      this.code = "unknown_error";
    }
    this.status = status;
    this.name = "ApiError";
  }
}

export async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorData: any;
    try {
      errorData = await res.json();
      if (errorData?.detail) {
        errorData = errorData.detail;
      }
    } catch {
      errorData = await res.text();
    }
    throw new ApiError(res.status, errorData);
  }

  return res.json() as Promise<T>;
}
