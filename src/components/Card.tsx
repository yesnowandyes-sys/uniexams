"use client";

import { CSSProperties, ReactNode } from "react";
import { C, SH } from "@/lib/constants";

/** Card — white surface with border and shadow */
export function Card({
  children,
  style,
  className,
  radius = 14,
  padding = "1.5rem",
}: {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
  radius?: number;
  padding?: string;
}) {
  return (
    <div
      className={className}
      style={{
        background: C.surf,
        borderRadius: radius,
        border: `1px solid ${C.bdr}`,
        padding,
        boxShadow: SH.card,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
