"use client";

import { C, RadarPoint } from "@/lib/constants";

/** SVG Radar Chart — no recharts dependency */
export function RadarChartSVG({ data }: { data: RadarPoint[] }) {
  const size = 260;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 72;
  const levels = [0.25, 0.5, 0.75, 1.0];

  const angleFor = (i: number) => {
    const n = data.length;
    return (Math.PI * 2 * i) / n - Math.PI / 2;
  };

  const pointFor = (i: number, val: number): [number, number] => {
    const angle = angleFor(i);
    const r = maxR * (val / 100);
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  };

  // Grid rings
  const rings = levels.map((lv, li) => {
    const pts = data
      .map((_, i) => {
        const angle = angleFor(i);
        const r = maxR * lv;
        return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
      })
      .join(" ");
    return (
      <polygon
        key={li}
        points={pts}
        fill="none"
        stroke={C.bdr}
        strokeWidth="1"
        strokeDasharray="3 3"
      />
    );
  });

  // Axes
  const axes = data.map((_, i) => {
    const angle = angleFor(i);
    const x = cx + maxR * Math.cos(angle);
    const y = cy + maxR * Math.sin(angle);
    return (
      <line
        key={i}
        x1={cx}
        y1={cy}
        x2={x}
        y2={y}
        stroke={C.bdr}
        strokeWidth="1"
      />
    );
  });

  // Data polygon
  const dataPts = data
    .map((d, i) => pointFor(i, d.v))
    .map(([x, y]) => `${x},${y}`)
    .join(" ");

  // Data dots
  const dots = data.map((d, i) => {
    const [x, y] = pointFor(i, d.v);
    return (
      <circle
        key={i}
        cx={x}
        cy={y}
        r="3.5"
        fill={C.mid}
        strokeWidth="0"
      />
    );
  });

  // Labels
  const labels = data.map((d, i) => {
    const angle = angleFor(i);
    const lr = maxR + 18;
    const x = cx + lr * Math.cos(angle);
    const y = cy + lr * Math.sin(angle);
    const anchor =
      Math.abs(Math.cos(angle)) < 0.3
        ? "middle"
        : Math.cos(angle) > 0
        ? "start"
        : "end";
    return (
      <text
        key={i}
        x={x}
        y={y}
        fontSize="11"
        fill={C.sec}
        fontFamily="Inter,sans-serif"
        fontWeight="500"
        textAnchor={anchor}
        dominantBaseline="middle"
      >
        {d.axis}
      </text>
    );
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {rings}
      {axes}
      <polygon
        points={dataPts}
        fill={C.mid}
        fillOpacity="0.1"
        stroke={C.mid}
        strokeWidth="2"
      />
      {dots}
      {labels}
    </svg>
  );
}
