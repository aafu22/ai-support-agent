"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api";

export function useFetch<T>(path: string | null, pollMs?: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(path !== null);

  const load = useCallback(
    async (silent = false) => {
      if (path === null) return;
      if (!silent) setLoading(true);
      try {
        setData(await api<T>(path));
        setError(null);
      } catch (e) {
        setError(e instanceof ApiError ? e : new ApiError(0, "Network error"));
      } finally {
        setLoading(false);
      }
    },
    [path],
  );

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!pollMs || path === null) return;
    const t = setInterval(() => load(true), pollMs);
    return () => clearInterval(t);
  }, [load, pollMs, path]);

  return { data, error, loading, reload: () => load(true), setData };
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
