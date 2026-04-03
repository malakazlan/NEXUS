"use client";

import useSWR, { type SWRConfiguration } from "swr";

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
};

export function useFetch<T>(
  path: string | null,
  opts?: SWRConfiguration
) {
  return useSWR<T>(path ? `/api${path}` : null, fetcher, {
    refreshInterval: 3000,
    revalidateOnFocus: true,
    ...opts,
  });
}
