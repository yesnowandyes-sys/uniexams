"use client";

import { C } from "@/lib/constants";

/** ProgressBar — thin progress stripe with smooth fill animation */
export function ProgressBar({
  pct,
  color,
  h = 2,
  radius = 1,
  showTrack = true,
}: {
  pct: number;
  color: string;
  h?: number;
  radius?: number;
  showTrack?: boolean;
}) {
  return (
    <div
      style={{
        height: h,
        borderRadius: radius,
        background: showTrack ? C.bdr : "transparent",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "100%",
          borderRadius: radius,
          width: `${Math.min(100, Math.max(0, pct))}%`,
          background: color,
          transition: "width 0.45s cubic-bezier(0.16,1,0.3,1), background 0.3s",
        }}
      />
    </div>
  );
}
