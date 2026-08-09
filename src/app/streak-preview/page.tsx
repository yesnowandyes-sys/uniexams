"use client";

import { C } from "@/lib/constants";
import { Svg } from "@/components/icons";
import { Card } from "@/components/Card";
import { StatCard } from "@/components/StatCard";
import styles from "../page.module.css";

/* Temporary design-review route — not linked from nav, delete once a
   direction is picked. Renders real variants of the Day Streak tile
   inside the actual 256px stat column, next to the app's real fonts,
   tokens, and neighbouring StatCards. */

const cardBase: React.CSSProperties = {
  background: C.surf,
  border: `1px solid ${C.bdr}`,
  borderRadius: 12,
  padding: "14px 16px",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)",
  display: "flex",
  flexDirection: "column",
  gap: 10,
};

const weekLabels = ["M", "T", "W", "T", "F", "S", "S"];

function DayCell({
  state,
  label,
}: {
  state: "done" | "today" | "future" | "frozen";
  label: string;
}) {
  const box: React.CSSProperties = {
    width: 24,
    height: 27,
    borderRadius: 7,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };
  if (state === "done") {
    box.background = C.amber;
  } else if (state === "today") {
    box.background = "#fff";
    box.border = `1.5px solid ${C.mid}`;
    box.boxShadow = `0 0 0 3px ${C.liteb}`;
  } else if (state === "frozen") {
    box.background = C.aLite;
    box.border = `1.5px dashed ${C.aBdr}`;
  } else {
    box.background = C.alt;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <div style={box}>
        {state === "done" && <Svg icon="check" size={10} col="#fff" sw={2.5} />}
        {state === "frozen" && <Svg icon="checkCir" size={10} col={C.amber} sw={2} />}
      </div>
      <span style={{ fontSize: "0.5625rem", fontWeight: 600, color: C.ter }}>{label}</span>
    </div>
  );
}

function VariantA_OnBrandGrid() {
  const states: ("done" | "today" | "future" | "frozen")[] = [
    "done", "done", "done", "done", "today", "future", "future",
  ];
  return (
    <div style={cardBase}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: C.aLite, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Svg icon="flame" size={15} col={C.amber} sw={1.8} />
        </div>
        <span style={{ fontSize: "0.6875rem", fontWeight: 600, padding: "2px 6px", borderRadius: 4, color: C.ter, background: C.alt }}>
          best 27
        </span>
      </div>
      <div>
        <div style={{ fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ter, marginBottom: 4 }}>
          Day Streak
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.875rem", fontWeight: 700, lineHeight: 1, color: C.amber }}>12</span>
          <span style={{ fontSize: "0.75rem", fontWeight: 500, color: C.ter }}>days</span>
        </div>
      </div>
      <div style={{ display: "flex", gap: 5, marginTop: 2 }}>
        {weekLabels.map((l, i) => (
          <DayCell key={i} state={states[i]} label={l} />
        ))}
      </div>
    </div>
  );
}

function VariantB_Ring() {
  const r = 20;
  const circ = 2 * Math.PI * r;
  const pct = 12 / 14;
  return (
    <div style={cardBase}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ter }}>
          Day Streak
        </span>
        <span style={{ fontSize: "0.625rem", fontWeight: 600, color: C.amber, background: C.aLite, border: `1px solid ${C.aBdr}`, padding: "2px 6px", borderRadius: 4 }}>
          2 to Tier 2
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <svg width="48" height="48" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r={r} fill="none" stroke={C.alt} strokeWidth="4.5" />
          <circle
            cx="24" cy="24" r={r} fill="none" stroke={C.amber} strokeWidth="4.5"
            strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ * (1 - pct)}
            transform="rotate(-90 24 24)"
          />
          <g transform="translate(13.5,13.5)">
            <Svg icon="flame" size={21} col={C.amber} sw={1.8} />
          </g>
        </svg>
        <div>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.375rem", fontWeight: 700, color: C.amber, lineHeight: 1 }}>
            12<span style={{ fontSize: "0.75rem", fontWeight: 500, color: C.ter }}> days</span>
          </div>
          <div style={{ fontSize: "0.625rem", color: C.ter, marginTop: 3 }}>86% to next tier</div>
        </div>
      </div>
    </div>
  );
}

function VariantC_Split() {
  return (
    <div style={cardBase}>
      <div style={{ fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ter }}>
        Day Streak
      </div>
      <div style={{ display: "flex", alignItems: "stretch" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "0.625rem", color: C.ter }}>Current</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.375rem", fontWeight: 700, color: C.amber }}>12</span>
            <span style={{ fontSize: "0.6875rem", color: C.ter }}>days</span>
          </div>
        </div>
        <div style={{ width: 1, background: C.bdr, margin: "2px 12px" }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "0.625rem", color: C.ter }}>Best</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.375rem", fontWeight: 700, color: C.sec }}>27</span>
            <span style={{ fontSize: "0.6875rem", color: C.ter }}>days</span>
          </div>
        </div>
      </div>
      <div style={{ height: 4, background: C.alt, borderRadius: 2, overflow: "hidden" }}>
        <div style={{ height: "100%", width: "44%", background: C.amber, borderRadius: 2 }} />
      </div>
    </div>
  );
}

function VariantD_Freeze() {
  const states: ("done" | "today" | "future" | "frozen")[] = [
    "done", "done", "frozen", "done", "today", "future", "future",
  ];
  return (
    <div style={cardBase}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: C.aLite, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Svg icon="flame" size={15} col={C.amber} sw={1.8} />
        </div>
        <span style={{ fontSize: "0.6875rem", fontWeight: 600, padding: "2px 6px", borderRadius: 4, color: C.amber, background: C.aLite }}>
          1 freeze left
        </span>
      </div>
      <div>
        <div style={{ fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ter, marginBottom: 4 }}>
          Day Streak
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.875rem", fontWeight: 700, lineHeight: 1, color: C.amber }}>12</span>
          <span style={{ fontSize: "0.75rem", fontWeight: 500, color: C.ter }}>days</span>
        </div>
      </div>
      <div style={{ display: "flex", gap: 5, marginTop: 2 }}>
        {weekLabels.map((l, i) => (
          <DayCell key={i} state={states[i]} label={l} />
        ))}
      </div>
    </div>
  );
}

function VariantE_Lane() {
  const states: ("done" | "today" | "future" | "frozen")[] = [
    "done", "done", "done", "done", "today", "future", "future",
  ];
  return (
    <div
      style={{
        background: C.surf,
        border: `1px solid ${C.bdr}`,
        borderLeft: `4px solid ${C.amber}`,
        borderRadius: "0 12px 12px 0",
        padding: "20px 24px",
        boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)",
        display: "flex",
        alignItems: "center",
        gap: 32,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0, width: 200 }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ter, marginBottom: 4 }}>
            Day Streak
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "2.25rem", fontWeight: 700, lineHeight: 1, color: C.amber }}>12</span>
            <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: C.ter }}>days running</span>
          </div>
          <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: C.sec }}>personal best 27</span>
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {weekLabels.map((l, i) => (
          <DayCell key={i} state={states[i]} label={l} />
        ))}
      </div>
    </div>
  );
}

function Row({
  label,
  note,
  Variant,
}: {
  label: string;
  note: string;
  Variant: React.ComponentType;
}) {
  return (
    <section style={{ marginBottom: 40 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10 }}>
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.75rem", fontWeight: 700, color: C.amber, background: C.aLite, border: `1px solid ${C.aBdr}`, padding: "2px 8px", borderRadius: 5 }}>
          {label}
        </span>
        <span style={{ fontSize: "0.8125rem", color: C.sec }}>{note}</span>
      </div>
      <div className={styles.mainGrid}>
        <Card>
          <div style={{ height: 380, display: "flex", alignItems: "center", justifyContent: "center", color: C.ter, fontSize: "0.8125rem" }}>
            Knowledge Map (unchanged)
          </div>
        </Card>
        <div className={styles.statCardsCol}>
          <Variant />
          <StatCard icon="clock" label="Avg Time / Q" val="1:24" unit="min" col={C.mid} bg={C.lite} delta="41 ans" deltaCol={C.ter} />
          <StatCard icon="trendUp" label="Accuracy" val="78" unit="%" col={C.green} bg={C.gLite} delta="strong" deltaCol={C.green} />
          <StatCard icon="sparkle" label="Questions Done" val="41" unit="total" col={C.purp} bg={C.pLite} delta="32 ✓" deltaCol={C.green} />
        </div>
      </div>
    </section>
  );
}

export default function StreakPreviewPage() {
  return (
    <div className={styles.page}>
      <main className={styles.main} style={{ paddingTop: "2rem" }}>
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: "1.625rem", fontWeight: 700, letterSpacing: "-0.025em", color: C.text, margin: "0 0 8px" }}>
            Day Streak — real-context options
          </h1>
          <p style={{ fontSize: "0.875rem", color: C.sec, maxWidth: 640, lineHeight: 1.6 }}>
            Each row swaps only the Day Streak tile (top-left of the stat column) for a
            variant, leaving the real Avg Time/Q, Accuracy, and Questions Done tiles and
            the real page chrome untouched, so sizing and colour read exactly as they
            would in the live dashboard.
          </p>
        </div>

        <Row label="A" note="On-brand grid — same footprint, weekly dots, best-streak delta" Variant={VariantA_OnBrandGrid} />
        <Row label="B" note="Milestone ring — arc toward the next 14-day tier" Variant={VariantB_Ring} />
        <Row label="C" note="Current / best split with a share-of-best bar" Variant={VariantC_Split} />
        <Row label="D" note="Grid with a freeze state on the missed Wednesday" Variant={VariantD_Freeze} />

        <section style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10 }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.75rem", fontWeight: 700, color: C.amber, background: C.aLite, border: `1px solid ${C.aBdr}`, padding: "2px 8px", borderRadius: 5 }}>
              E
            </span>
            <span style={{ fontSize: "0.8125rem", color: C.sec }}>
              Hero lane — breaks out of the stat column into its own full-width row (structural change)
            </span>
          </div>
          <VariantE_Lane />
        </section>
      </main>
    </div>
  );
}
