"use client";

import { useState, useEffect } from "react";

/**
 * Custom hook that returns true when the viewport matches the given media query.
 * Defaults to `false` during SSR to avoid hydration mismatches.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

/** Pre-built breakpoint predicates — use these instead of raw strings. */
export const BREAKPOINTS = {
  tablet: "(max-width: 860px)",
  mobile: "(max-width: 480px)",
  smallPhone: "(max-width: 375px)",
} as const;
