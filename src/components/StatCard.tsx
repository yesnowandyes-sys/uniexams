"use client";

import { C } from "@/lib/constants";
import { Svg, IconName } from "./icons";
import { Label } from "./atoms";
import styles from "./StatCard.module.css";

interface StatCardProps {
  icon: IconName;
  label: string;
  val: string;
  unit?: string;
  col: string;
  bg: string;
  delta: string;
  deltaCol: string;
}

/** StatCard — displays a metric with icon, JetBrains Mono number, and delta.
 *
 *  All structural layout lives in StatCard.module.css (the card owns its own
 *  internal flex column), but the card deliberately does NOT set a `flex`
 *  size: the parent layout decides how the card is sized so responsive
 *  breakpoints (e.g. the dashboard's `.statCardsCol > *` 2×2 wrap) can take
 *  effect. Only the per-card accent colours stay inline — they are dynamic. */
export function StatCard({
  icon,
  label,
  val,
  unit,
  col,
  bg,
  delta,
  deltaCol,
}: StatCardProps) {
  return (
    <div className={`stat-card ${styles.card}`}>
      <div className={styles.topRow}>
        <div className={styles.iconBox} style={{ background: bg }}>
          <Svg icon={icon} size={15} col={col} sw={1.8} />
        </div>
        <span
          className={styles.delta}
          style={{
            color: deltaCol,
            background: deltaCol === C.green ? C.gLite : C.lite,
          }}
        >
          {delta}
        </span>
      </div>
      <div>
        <Label col={C.ter} mb={4}>
          {label}
        </Label>
        <div className={styles.valRow}>
          <span className={styles.val} style={{ color: col }}>
            {val}
          </span>
          {unit && <span className={styles.unit}>{unit}</span>}
        </div>
      </div>
    </div>
  );
}
