"use client";

import { useId } from "react";
import { C, RadarPoint, tierColor } from "@/lib/constants";
import styles from "./RadarChartSVG.module.css";

/** SVG radar/spider chart — no charting library dependency */
export function RadarChartSVG({ data }: { data: RadarPoint[] }) {
  const uid = useId();
  const size = 260;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 76;
  const labelR = maxR + 20;
  const levels = [0.25, 0.5, 0.75, 1.0];
  const n = data.length;

  const angleFor = (i: number) => (Math.PI * 2 * i) / n - Math.PI / 2;

  const pointFor = (i: number, val: number): [number, number] => {
    const angle = angleFor(i);
    const r = maxR * (val / 100);
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  };

  const dataPts = data
    .map((d, i) => pointFor(i, d.v))
    .map(([x, y]) => `${x},${y}`)
    .join(" ");

  const fillId = `rc-fill-${uid}`;
  const glowId = `rc-glow-${uid}`;
  const dotShadowId = `rc-dot-shadow-${uid}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{ overflow: "visible" }}
      role="img"
      aria-label="Accuracy by module radar chart"
    >
      <defs>
        <radialGradient id={fillId} cx="50%" cy="42%" r="65%">
          <stop offset="0%" stopColor={C.mid} stopOpacity="0.22" />
          <stop offset="100%" stopColor={C.mid} stopOpacity="0.04" />
        </radialGradient>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor={C.mid} floodOpacity="0.18" />
        </filter>
        <filter id={dotShadowId} x="-100%" y="-100%" width="300%" height="300%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.4" floodColor="#0F172A" floodOpacity="0.25" />
        </filter>
      </defs>

      {/* Concentric grid rings */}
      {levels.map((lv, li) => (
        <circle
          key={li}
          cx={cx}
          cy={cy}
          r={maxR * lv}
          fill="none"
          stroke={C.bdr}
          strokeWidth={li === levels.length - 1 ? 1.25 : 1}
          opacity={li === levels.length - 1 ? 0.9 : 0.55}
        />
      ))}

      {/* Axis spokes */}
      {data.map((_, i) => {
        const angle = angleFor(i);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={cx + maxR * Math.cos(angle)}
            y2={cy + maxR * Math.sin(angle)}
            stroke={C.bdr}
            strokeWidth="1"
            opacity="0.6"
          />
        );
      })}

      <circle cx={cx} cy={cy} r="2" fill={C.bdr2} />

      {/* Data shape */}
      <polygon
        className={styles.dataShape}
        points={dataPts}
        fill={`url(#${fillId})`}
        stroke={C.mid}
        strokeWidth="2.25"
        strokeLinejoin="round"
        filter={`url(#${glowId})`}
      />

      {/* Data points, colour-coded by the same accuracy tiers as the bars beside the chart */}
      {data.map((d, i) => {
        const [x, y] = pointFor(i, d.v);
        const col = tierColor(d.v);
        return (
          <circle
            key={i}
            className={styles.dot}
            style={{ animationDelay: `${0.15 + i * 0.05}s` }}
            cx={x}
            cy={y}
            r="4.5"
            fill={col}
            stroke={C.surf}
            strokeWidth="2.5"
            filter={`url(#${dotShadowId})`}
          />
        );
      })}

      {/* Labels: module name + colour-coded accuracy */}
      {data.map((d, i) => {
        const angle = angleFor(i);
        const x = cx + labelR * Math.cos(angle);
        const y = cy + labelR * Math.sin(angle);
        const anchor =
          Math.abs(Math.cos(angle)) < 0.35
            ? "middle"
            : Math.cos(angle) > 0
            ? "start"
            : "end";
        const col = tierColor(d.v);
        return (
          <g key={i} textAnchor={anchor}>
            <text
              x={x}
              y={y - 5}
              fontSize="11.5"
              fontWeight="600"
              fill={C.text}
              fontFamily="Inter, sans-serif"
              dominantBaseline="middle"
            >
              {d.axis}
            </text>
            <text
              x={x}
              y={y + 10}
              fontSize="10.5"
              fontWeight="700"
              fill={col}
              fontFamily="'JetBrains Mono', monospace"
              dominantBaseline="middle"
            >
              {d.v > 0 ? `${d.v}%` : "—"}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
