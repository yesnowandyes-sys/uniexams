"use client";

import { C } from "@/lib/constants";
import { Svg } from "./icons";
import styles from "./atoms.module.css";

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
      className={styles.pill}
      style={{
        background: bg,
        color: col,
        border: `1px solid ${bdr || bg}`,
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
      className={styles.kbd}
      style={{
        background: C.surf,
        border: `1px solid ${C.bdr2}`,
        borderBottom: `2px solid ${C.bdr2}`,
        color: C.sec,
      }}
    >
      {children}
    </span>
  );
}

/** Wordmark — ESAT Gymnasium logo */
export function Wordmark() {
  return (
    <div className={styles.wordmark}>
      <div
        className={styles.wordmarkIcon}
        style={{
          background: C.blue,
          boxShadow:
            "inset 0 1px 0 rgba(255,255,255,0.12), 0 1px 3px rgba(26,71,184,0.3)",
        }}
      >
        <span className={styles.wordmarkG}>G</span>
      </div>
      <div className={styles.wordmarkText}>
        <span className={styles.wordmarkEsat} style={{ color: C.text }}>
          ESAT
        </span>
        <span
          className={styles.wordmarkGymnasium}
          style={{ color: C.blue }}
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
      className={styles.label}
      style={{ color: col, marginBottom: mb, marginTop: mt }}
    >
      {children}
    </div>
  );
}

/** Navigation pill — used in the Dashboard header.
 *  Layout lives in the module (.navPill); the global `nav-pill` class still
 *  provides hover/active background, and the dynamic active colour/weight
 *  stay inline. */
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

  const className = `${styles.navPill} nav-pill${active ? " active" : ""}`;
  const style = {
    fontWeight: active ? 600 : 500,
    color: active ? C.mid : C.sec,
  } as const;

  if (href) {
    return (
      <a href={href} className={className} style={style}>
        {content}
      </a>
    );
  }

  return (
    <div className={className} style={style}>
      {content}
    </div>
  );
}
