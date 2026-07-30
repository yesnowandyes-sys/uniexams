"use client";

import { CSSProperties, ReactNode } from "react";
import { C, SH } from "@/lib/constants";

/** QuestionCard — white card with the Gymnasium Lane (5px blue left border) */
export function QuestionCard({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        background: C.surf,
        borderTop: `1px solid ${C.bdr}`,
        borderRight: `1px solid ${C.bdr}`,
        borderBottom: `1px solid ${C.bdr}`,
        borderLeft: `5px solid ${C.mid}`,
        borderRadius: "0 12px 12px 0",
        padding: "1.5rem 1.75rem",
        boxShadow: SH.card,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
