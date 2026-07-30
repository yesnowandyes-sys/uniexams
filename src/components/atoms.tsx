"use client";

import { C } from "@/lib/constants";
import { Svg } from "./icons";

/* ═══════════════════════════════════════════════════════════════════
   ATOMS
   ═══════════════════════════════════════════════════════════════════ */

/** Progress bar — used in Dashboard and Practice Hub sidebar */
export function Bar({
  pct,
  color,
  h = 3,
}: {
  pct: number;
  color: string;
  h?: number;
}) {
  return (
    <div
      style={{
        height: h,
        borderRadius: h,
        background: C.bdr,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${Math.min(100, Math.max(0, pct))}%`,
          background: color,
          borderRadius: h,
          transition: "width 0.55s cubic-bezier(0.16,1,0.3,1)",
        }}
      />
    </div>
  );
}

/** Pill badge — difficulty tags, meta info */
export function Pill({
  children,
  bg,
  col,
  bdr,
}: {
  children: React.ReactNode;
  bg: string;
  col: string;
  bdr?: string;
}) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        height: 22,
        padding: "0 8px",
        borderRadius: 5,
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.01em",
        background: bg,
        color: col,
        border: `1px solid ${bdr || bg}`,
        whiteSpace: "nowrap",
        lineHeight: 1,
        userSelect: "none",
      }}
    >
      {children}
    </span>
  );
}

/** Keyboard key badge — styled like actual key caps */
export function KBD({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 20,
        height: 20,
        padding: "0 5px",
        background: C.surf,
        border: `1px solid ${C.bdr2}`,
        borderBottom: `2px solid ${C.bdr2}`,
        borderRadius: 4,
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: "0.625rem",
        fontWeight: 600,
        color: C.sec,
        lineHeight: 1,
      }}
    >
      {children}
    </span>
  );
}

/** Wordmark — ESAT Gymnasium logo */
export function Wordmark() {
  return (
    <div
      style={{ display: "flex", alignItems: "center", gap: 10, userSelect: "none" }}
    >
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 9,
          background: C.blue,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          boxShadow:
            "inset 0 1px 0 rgba(255,255,255,0.12), 0 1px 3px rgba(26,71,184,0.3)",
        }}
      >
        <span
          style={{
            fontFamily: '"Instrument Serif", serif',
            fontStyle: "italic",
            fontSize: "1.45rem",
            color: "#fff",
            lineHeight: 1,
            marginTop: 1,
            display: "block",
          }}
        >
          G
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 5, lineHeight: 1 }}>
        <span
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: "0.875rem",
            fontWeight: 700,
            color: C.text,
            letterSpacing: "0.07em",
          }}
        >
          ESAT
        </span>
        <span
          style={{
            fontFamily: '"Instrument Serif", serif',
            fontStyle: "italic",
            fontSize: "1.1rem",
            color: C.blue,
            letterSpacing: "-0.01em",
          }}
        >
          Gymnasium
        </span>
      </div>
    </div>
  );
}

/** Section label — small caps eyebrow style */
export function Label({
  children,
  col = C.ter,
  mb = 0,
  mt = 0,
}: {
  children: React.ReactNode;
  col?: string;
  mb?: number;
  mt?: number;
}) {
  return (
    <div
      style={{
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: col,
        marginBottom: mb,
        marginTop: mt,
      }}
    >
      {children}
    </div>
  );
}

/** Navigation pill — used in the Dashboard header */
export function NavPill({
  label,
  icon,
  active = false,
  href,
}: {
  label: string;
  icon: "squares" | "bolt" | "activity" | "pencil";
  active?: boolean;
  href?: string;
}) {
  const content = (
    <>
      <Svg icon={icon} size={14} col="currentColor" />
      {label}
    </>
  );

  if (href) {
    return (
      <a
        href={href}
        className={`nav-pill${active ? " active" : ""}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: "0.8125rem",
          fontWeight: active ? 600 : 500,
          color: active ? C.mid : C.sec,
          textDecoration: "none",
        }}
      >
        {content}
      </a>
    );
  }

  return (
    <div
      className={`nav-pill${active ? " active" : ""}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        fontSize: "0.8125rem",
        fontWeight: active ? 600 : 500,
        color: active ? C.mid : C.sec,
      }}
    >
      {content}
    </div>
  );
}
