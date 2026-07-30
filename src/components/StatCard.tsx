"use client";

import { C } from "@/lib/constants";
import { Svg, IconName } from "./icons";
import { Label } from "./atoms";

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

/** StatCard — displays a metric with icon, JetBrains Mono number, and delta */
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
    <div
      className="stat-card"
      style={{
        flex: 1,
        background: C.surf,
        border: `1px solid ${C.bdr}`,
        borderRadius: 12,
        padding: "14px 16px",
        boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: 8,
            background: bg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Svg icon={icon} size={15} col={col} sw={1.8} />
        </div>
        <span
          style={{
            fontSize: "0.6875rem",
            fontWeight: 600,
            fontFamily: '"JetBrains Mono", monospace',
            color: deltaCol,
            background: deltaCol === C.green ? C.gLite : C.lite,
            padding: "2px 6px",
            borderRadius: 4,
          }}
        >
          {delta}
        </span>
      </div>
      <div>
        <Label col={C.ter} mb={4}>
          {label}
        </Label>
        <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
          <span
            style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: "1.875rem",
              fontWeight: 700,
              color: col,
              lineHeight: 1,
            }}
          >
            {val}
          </span>
          {unit && (
            <span
              style={{
                fontSize: "0.75rem",
                color: C.ter,
                fontWeight: 500,
              }}
            >
              {unit}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
