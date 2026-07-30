import { useState, useEffect, useRef } from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";

/* ═══════════════════════════════════════════════════════════════════
 DESIGN TOKENS
 Palette: warm off-white ground · pure white cards · authoritative
 navy + interactive cobalt · JetBrains Mono for all numeric data.
 Shadows replace most borders — depth over decoration.
═══════════════════════════════════════════════════════════════════ */
const C = {
  bg: "#F6F5F1", surf: "#FFFFFF", alt: "#EFECEA",
  bdr: "#E3E0DA", bdr2: "#C9C6C0",
  text: "#18181A", sec: "#504F4C", ter: "#9E9C98",
  blue: "#1A47B8", mid: "#2563EB", lite: "#EEF4FF", liteb: "#DBEAFE",
  green: "#15803D", gLite: "#F0FDF4", gBdr: "#86EFAC",
  red: "#DC2626", rLite: "#FEF2F2", rBdr: "#FECACA",
  amber: "#B45309", aLite: "#FFFBEB", aBdr: "#FDE68A",
  purp: "#7C3AED", pLite: "#F5F3FF", pBdr: "#DDD6FE",
};
const SH = {
  card: "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)",
  lifted: "0 3px 10px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)",
  blue: "0 4px 14px rgba(37,99,235,0.22), 0 1px 3px rgba(37,99,235,0.12)",
};

/* ═══════════════════════════════════════════════════════════════════
 CONSTANTS
═══════════════════════════════════════════════════════════════════ */
const EXAM_DATE = new Date("2026-10-09");
const DAYS_LEFT = Math.max(0, Math.ceil((EXAM_DATE - Date.now()) / 86400000));
const SESSION = 10;

const TOPICS = {
  "Mathematics 1": [
    { name: "Algebra & Polynomials", str: 72 },
    { name: "Sequences & Series", str: 59 },
    { name: "Geometry & Trigonometry", str: 85 },
    { name: "Statistics & Probability", str: 64 },
    { name: "Calculus", str: 57 },
  ],
  "Physics": [
    { name: "Mechanics", str: 78 },
    { name: "Electricity & Magnetism", str: 44 },
    { name: "Waves & Optics", str: 67 },
    { name: "Thermodynamics", str: 51 },
    { name: "Modern Physics", str: 63 },
  ],
  "Chemistry": [
    { name: "Atomic Structure", str: 86 },
    { name: "Energetics & Kinetics", str: 68 },
    { name: "Organic Chemistry", str: 71 },
    { name: "Equilibrium & Acids", str: 59 },
  ],
  "Biology": [
    { name: "Cell Biology", str: 83 },
    { name: "Genetics & Inheritance", str: 76 },
    { name: "Ecology & Populations", str: 90 },
    { name: "Human Physiology", str: 68 },
  ],
  "Mathematics 2": [
    { name: "Proof & Logic", str: 41 },
    { name: "Complex Numbers", str: 60 },
    { name: "Differential Equations", str: 53 },
    { name: "Number Theory", str: 47 },
  ],
};

const RADAR_DATA = [
  { axis: "Maths 1", v: 67 },
  { axis: "Physics", v: 61 },
  { axis: "Chemistry", v: 71 },
  { axis: "Biology", v: 79 },
  { axis: "Maths 2", v: 50 },
];

const DIFF_META = {
  "Easy": { bg: "#F0FDF4", col: "#15803D", bdr: "#86EFAC" },
  "Medium": { bg: "#FFFBEB", col: "#B45309", bdr: "#FDE68A" },
  "Hard": { bg: "#FEF2F2", col: "#DC2626", bdr: "#FECACA" },
  "Very Hard": { bg: "#F5F3FF", col: "#7C3AED", bdr: "#DDD6FE" },
};
const DIFF_SEQ = ["Easy","Medium","Medium","Hard","Medium","Hard","Hard","Very Hard","Medium","Very Hard"];

/* ═══════════════════════════════════════════════════════════════════
 API
═══════════════════════════════════════════════════════════════════ */
async function genQuestion(subject, topic, diff) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      system:
        "You write genuine ESAT (Engineering and Science Admissions Test) practice questions " +
        "for Cambridge, Imperial and UCL applicants. Questions are five-choice MCQ (A–E), " +
        "A-level+ difficulty, no calculator. Return ONLY compact JSON, no markdown, no backticks.",
      messages: [{
        role: "user",
        content:
          `Generate one ${diff}-difficulty ESAT question on "${topic}" (${subject}). ` +
          `Use unicode: ², ³, √, π, θ, φ, ∫, Δ, Σ, ∞, ≤, ≥, ≈, ≠, ⁻¹, μ, λ, ω, α, β, γ. Fractions as (a)/(b).\n` +
          `Return ONLY: {"q":"...","opts":["A) ...","B) ...","C) ...","D) ...","E) ..."],` +
          `"ans":"B","topic":"${topic}","diff":"${diff}","hint":"strategic hint without spoiling",` +
          `"soln":"step-by-step worked solution"}`,
      }],
    }),
  });
  const d = await res.json();
  const raw = (d.content?.[0]?.text || "{}").replace(/```[a-z]*/gi,"").replace(/```/g,"").trim();
  return JSON.parse(raw);
}

/* ═══════════════════════════════════════════════════════════════════
 ICON SYSTEM
 Heroicons-derived · 24×24 viewBox · 1.6px stroke · round caps
═══════════════════════════════════════════════════════════════════ */
const P = {
  flame: ["M15.362 5.214A8.252 8.252 0 0 1 12 21 8.25 8.25 0 0 1 6.038 7.047 8.287 8.287 0 0 0 9 9.601a8.983 8.983 0 0 1 3.361-6.867 8.21 8.21 0 0 0 3 2.48Z",
    "M12 18a3.75 3.75 0 0 0 .495-7.468 5.99 5.99 0 0 0-1.925 3.547 5.975 5.975 0 0 1-2.133-1.001A3.75 3.75 0 0 0 12 18Z"],
  clock: ["M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"],
  trendUp: ["M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941"],
  checkCir: ["M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"],
  xCir: ["m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"],
  check: ["M4.5 12.75l6 6 9-13.5"],
  x: ["M6 18 18 6M6 6l12 12"],
  chevL: ["M15.75 19.5 8.25 12l7.5-7.5"],
  chevR: ["M8.25 4.5l7.5 7.5-7.5 7.5"],
  chevD: ["M19.5 8.25l-7.5 7.5-7.5-7.5"],
  arrowL: ["M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"],
  play: ["M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"],
  bulb: ["M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"],
  book: ["M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"],
  warn: ["M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"],
  squares: ["M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"],
  activity: ["M3 13.5h3.75l3-9.75 4.5 19.5 3-9.75H21"],
  trophy: ["M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"],
  pencil: ["m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125"],
  user: ["M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"],
  sparkle: ["M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z","M18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z"],
  bolt: ["M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"],
};

function Svg({ icon, size = 16, col = "currentColor", sw = 1.6, fill = "none", style = {} }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill={fill} stroke={col} strokeWidth={sw}
      strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true"
      style={{ display:"block", flexShrink:0, ...style }}
    >
      {(P[icon] || []).map((d, i) => <path key={i} d={d} />)}
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════
 GLOBAL STYLES — injected once, shared between pages
═══════════════════════════════════════════════════════════════════ */
const GCSS = `
  @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@1&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; }
  body { margin:0; -webkit-font-smoothing:antialiased; }

  /* Interactive transitions */
  .opt-btn {
    transition: background 0.1s ease, border-color 0.12s ease, box-shadow 0.12s ease;
    cursor: pointer;
    position: relative;
  }
  .opt-btn:hover:not(.answered) {
    background: #EEF4FF !important;
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px #EEF4FF;
  }
  .nav-pill {
    transition: color 0.1s, background 0.1s;
    cursor: pointer;
    border-radius: 6px;
    padding: 5px 10px;
  }
  .nav-pill:hover { background: #EFECEA; color: #18181A !important; }
  .nav-pill.active { color: #2563EB !important; background: #EEF4FF; }

  .topic-row { transition: background 0.1s; cursor: pointer; border-radius: 8px; }
  .topic-row:hover { background: #EFECEA; }
  .topic-row.focused { background: #EEF4FF; }

  .btn-primary {
    transition: filter 0.12s, box-shadow 0.12s, transform 0.1s;
    cursor: pointer;
  }
  .btn-primary:hover { filter: brightness(1.07); box-shadow: 0 4px 14px rgba(37,99,235,0.28); transform: translateY(-1px); }
  .btn-primary:active { transform: translateY(0); }

  .btn-ghost { transition: background 0.1s, border-color 0.1s; cursor: pointer; }
  .btn-ghost:hover { background: #EFECEA !important; border-color: #C9C6C0 !important; }

  .stat-card { transition: box-shadow 0.18s, transform 0.18s; }
  .stat-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.09) !important; transform: translateY(-2px); }

  .nav-btn { transition: background 0.1s, opacity 0.1s; }
  .nav-btn:not([disabled]):hover { background: #EFECEA !important; }

  .q-num-btn { transition: background 0.1s, border-color 0.1s, transform 0.1s; }
  .q-num-btn:hover { transform: scale(1.08); }

  .collapse-btn { transition: background 0.1s, border-color 0.12s; cursor: pointer; }
  .collapse-btn:hover { background: #EFECEA !important; }

  .hint-btn-open:hover { background: #FEF9C3 !important; }
  .soln-btn-open:hover { background: #DBEAFE !important; }

  /* Pulsing "now" dot */
  .pulse-dot { animation: pdot 2s ease-in-out infinite; }
  @keyframes pdot { 0%,100%{ opacity:1; transform:scale(1); } 50%{ opacity:0.45; transform:scale(0.75); } }

  /* Loading spinner */
  .spinner { animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Urgent timer pulse */
  .timer-urgent { animation: turg 0.9s ease-in-out infinite; }
  @keyframes turg { 0%,100%{ opacity:1; } 50%{ opacity:0.55; } }

  /* Custom select arrow */
  select {
    -webkit-appearance: none; appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239E9C98' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    padding-right: 32px !important;
  }
  select:focus { outline: none; border-color: #2563EB !important; box-shadow: 0 0 0 3px #EEF4FF; }
`;

function GlobalStyles() {
  useEffect(() => {
    if (document.getElementById("eg-gs")) return;
    const s = document.createElement("style");
    s.id = "eg-gs"; s.textContent = GCSS;
    document.head.appendChild(s);
  }, []);
  return null;
}

/* ═══════════════════════════════════════════════════════════════════
 ATOMS
═══════════════════════════════════════════════════════════════════ */
function Bar({ pct, color, h = 3 }) {
  return (
    <div style={{ height: h, borderRadius: h, background: C.bdr, overflow: "hidden" }}>
      <div style={{
        height: "100%",
        width: `${Math.min(100, Math.max(0, pct))}%`,
        background: color, borderRadius: h,
        transition: "width 0.55s cubic-bezier(0.16,1,0.3,1)",
      }} />
    </div>
  );
}

// Compact, typographically-tuned pill badge
function Pill({ children, bg, col, bdr }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", height: 22,
      padding: "0 8px", borderRadius: 5,
      fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.01em",
      background: bg, color: col, border: `1px solid ${bdr || bg}`,
      whiteSpace: "nowrap", lineHeight: 1, userSelect: "none",
    }}>
      {children}
    </span>
  );
}

// Keyboard key badge — styled like actual key caps
function KBD({ children }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      minWidth: 20, height: 20, padding: "0 5px",
      background: C.surf, border: `1px solid ${C.bdr2}`,
      borderBottom: `2px solid ${C.bdr2}`, borderRadius: 4,
      fontFamily: '"JetBrains Mono", monospace',
      fontSize: "0.625rem", fontWeight: 600, color: C.sec, lineHeight: 1,
    }}>
      {children}
    </span>
  );
}

// Wordmark — used in both pages
function Wordmark() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, userSelect: "none" }}>
      {/* Logo mark: italic G on navy — the Gymnasium initial */}
      <div style={{
        width: 34, height: 34, borderRadius: 9,
        background: C.blue,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.12), 0 1px 3px rgba(26,71,184,0.3)",
      }}>
        <span style={{
          fontFamily: '"Instrument Serif", serif', fontStyle: "italic",
          fontSize: "1.45rem", color: "#fff", lineHeight: 1,
          marginTop: 1, // optical vertical centering of the G descender
          display: "block",
        }}>G</span>
      </div>
      {/* Name: acronym in weight, word in italic serif */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 5, lineHeight: 1 }}>
        <span style={{
          fontFamily: "Inter, sans-serif", fontSize: "0.875rem",
          fontWeight: 700, color: C.text, letterSpacing: "0.07em",
        }}>ESAT</span>
        <span style={{
          fontFamily: '"Instrument Serif", serif', fontStyle: "italic",
          fontSize: "1.1rem", color: C.blue, letterSpacing: "-0.01em",
        }}>Gymnasium</span>
      </div>
    </div>
  );
}

// Section label — small caps eyebrow style
function Label({ children, col = C.ter, mb = 0 }) {
  return (
    <div style={{
      fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.08em",
      textTransform: "uppercase", color: col, marginBottom: mb,
    }}>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
 DASHBOARD
═══════════════════════════════════════════════════════════════════ */
function Dashboard({ onStart }) {

  const allTopics = Object.entries(TOPICS)
    .flatMap(([s, ts]) => ts.map(t => ({ ...t, s })))
    .sort((a, b) => a.str - b.str);
  const weak = allTopics.slice(0, 5);

  const STATS = [
    { icon: "flame", label: "Daily Streak", val: "12", unit: "days", col: C.amber, bg: "#FFF7ED", delta: "+2", deltaCol: C.green },
    { icon: "clock", label: "Avg Time / Q", val: "1:23", unit: "min", col: C.mid, bg: C.lite, delta: "−0:04", deltaCol: C.green },
    { icon: "trendUp", label: "Predicted Score", val: "7.2", unit: "/ 9", col: C.green, bg: C.gLite, delta: "+0.3", deltaCol: C.green },
    { icon: "sparkle", label: "Questions Done", val: "245", unit: "total", col: C.purp, bg: C.pLite, delta: "+45", deltaCol: C.mid },
  ];

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: C.bg, minHeight: "100vh" }}>
      <GlobalStyles />

      {/* ── Navigation bar ── */}
      <header style={{
        background: C.surf, height: 58,
        borderBottom: `1px solid ${C.bdr}`,
        display: "flex", alignItems: "center",
        padding: "0 2rem", position: "sticky", top: 0, zIndex: 100,
      }}>
        <Wordmark />
        <nav style={{ display: "flex", gap: 4, marginLeft: "2.5rem", alignItems: "center" }}>
          {[
            { label: "Dashboard", icon: "squares", active: true },
            { label: "Practice", icon: "bolt", active: false },
            { label: "Progress", icon: "activity", active: false },
          ].map(({ label, icon, active }) => (
            <div key={label} className={`nav-pill${active ? " active" : ""}`}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                fontSize: "0.8125rem", fontWeight: active ? 600 : 500,
                color: active ? C.mid : C.sec,
              }}
            >
              <Svg icon={icon} size={14} col="currentColor" />
              {label}
            </div>
          ))}
        </nav>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 7,
            background: C.aLite, border: `1px solid ${C.aBdr}`,
            borderRadius: 20, padding: "4px 10px 4px 7px",
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%", background: C.amber,
            }} className="pulse-dot" />
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: C.amber }}>
              12-day streak
            </span>
          </div>
          {/* Avatar */}
          <div style={{
            width: 32, height: 32, borderRadius: "50%",
            background: C.lite, border: `2px solid ${C.liteb}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer",
          }}>
            <Svg icon="user" size={14} col={C.mid} />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "2rem 2rem 3rem" }}>
        {/* Greeting */}
        <div style={{ marginBottom: "1.75rem" }}>
          <h2 style={{
            margin: "0 0 5px", fontSize: "1.625rem", fontWeight: 700,
            color: C.text, letterSpacing: "-0.025em",
          }}>
            Good morning, Alex.
          </h2>
          <p style={{ margin: 0, fontSize: "0.875rem", color: C.sec, lineHeight: 1.6 }}>
            {DAYS_LEFT} days to the ESAT. Your weakest area right now is{" "}
            <span style={{ fontWeight: 600, color: C.text }}>Proof &amp; Logic</span> — today's session targets it.
          </p>
        </div>

        {/* ── Countdown ── */}
        <div style={{
          background: C.blue, borderRadius: 14,
          padding: "1.375rem 1.875rem", marginBottom: "1.25rem",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          position: "relative", overflow: "hidden",
          boxShadow: "0 4px 24px rgba(26,71,184,0.18), 0 1px 4px rgba(26,71,184,0.12)",
        }}>
          {/* Decorative arcs — subtle depth */}
          <svg style={{ position:"absolute", right:-60, top:"50%", transform:"translateY(-50%)", opacity:0.055, pointerEvents:"none" }}
            width="320" height="320" viewBox="0 0 320 320" aria-hidden="true">
            <circle cx="160" cy="160" r="145" fill="none" stroke="white" strokeWidth="56"/>
          </svg>
          <svg style={{ position:"absolute", right:40, top:"50%", transform:"translateY(-50%)", opacity:0.04, pointerEvents:"none" }}
            width="160" height="160" viewBox="0 0 160 160" aria-hidden="true">
            <circle cx="80" cy="80" r="68" fill="none" stroke="white" strokeWidth="30"/>
          </svg>
          <div style={{ position: "relative" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              background: "rgba(255,255,255,0.12)", borderRadius: 20,
              padding: "3px 10px", marginBottom: 10,
            }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: "rgba(255,255,255,0.6)" }} />
              <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "rgba(255,255,255,0.7)", letterSpacing: "0.07em", textTransform: "uppercase" }}>
                ESAT 2026
              </span>
            </div>
            <div style={{
              fontSize: "1.125rem", fontWeight: 700, color: "#fff",
              letterSpacing: "-0.02em", marginBottom: 5,
            }}>
              Thursday, 9 October
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {["Cambridge", "Imperial College", "UCL"].map((u, i) => (
                <span key={u} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {i > 0 && <span style={{ color: "rgba(255,255,255,0.25)", fontSize: "0.75rem" }}>·</span>}
                  <span style={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" }}>{u}</span>
                </span>
              ))}
            </div>
          </div>
          <div style={{ textAlign: "right", position: "relative" }}>
            <div style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: "3.75rem", fontWeight: 700, color: "#fff",
              lineHeight: 1, letterSpacing: "-0.05em",
            }}>
              {DAYS_LEFT}
            </div>
            <div style={{
              fontSize: "0.6875rem", fontWeight: 600, color: "rgba(255,255,255,0.45)",
              letterSpacing: "0.08em", textTransform: "uppercase", marginTop: 5,
            }}>
              days remaining
            </div>
          </div>
        </div>

        {/* ── Main grid: Knowledge Map + Stat Cards ── */}
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 256px",
          gap: "1.25rem", marginBottom: "1.25rem",
        }}>
          {/* Knowledge Map */}
          <div style={{
            background: C.surf, borderRadius: 14,
            border: `1px solid ${C.bdr}`, padding: "1.5rem",
            boxShadow: SH.card,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
              <div>
                <h3 style={{ margin: "0 0 4px", fontSize: "0.9375rem", fontWeight: 600, color: C.text }}>
                  Knowledge Map
                </h3>
                <p style={{ margin: 0, fontSize: "0.8125rem", color: C.ter }}>
                  Accuracy by module · last 30 days
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {/* Overall average score badge */}
                <div style={{
                  display: "flex", flexDirection: "column", alignItems: "flex-end",
                  background: C.lite, border: `1px solid ${C.liteb}`,
                  borderRadius: 8, padding: "5px 10px",
                }}>
                  <span style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontSize: "1.125rem", fontWeight: 700, color: C.mid, lineHeight: 1,
                  }}>{Math.round(RADAR_DATA.reduce((s, d) => s + d.v, 0) / RADAR_DATA.length)}%</span>
                  <span style={{ fontSize: "0.625rem", color: C.ter, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", marginTop: 2 }}>avg</span>
                </div>
                <Pill bg={C.alt} col={C.sec}>245 questions</Pill>
              </div>
            </div>
            <div style={{ display: "flex", gap: "2rem", alignItems: "center" }}>
              <div style={{ flex: "0 0 220px", height: 210 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={RADAR_DATA} margin={{ top: 8, right: 22, bottom: 8, left: 22 }}>
                    <PolarGrid stroke={C.bdr} strokeDasharray="3 3" />
                    <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: C.sec, fontFamily: "Inter,sans-serif", fontWeight: 500 }} />
                    <Radar dataKey="v" stroke={C.mid} fill={C.mid} fillOpacity={0.1} strokeWidth={2}
                      dot={{ r: 3.5, fill: C.mid, strokeWidth: 0 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
                {RADAR_DATA.map(({ axis, v }) => {
                  const col = v >= 75 ? C.green : v >= 55 ? C.amber : C.red;
                  return (
                    <div key={axis}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, alignItems: "center" }}>
                        <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: C.text }}>{axis}</span>
                        <span style={{
                          fontFamily: '"JetBrains Mono", monospace',
                          fontSize: "0.75rem", fontWeight: 600, color: col,
                        }}>{v}%</span>
                      </div>
                      <Bar pct={v} color={col} />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Stat cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {STATS.map(({ icon, label, val, unit, col, bg, delta, deltaCol }) => (
              <div key={label} className="stat-card" style={{
                flex: 1, background: C.surf,
                border: `1px solid ${C.bdr}`, borderRadius: 12,
                padding: "14px 16px", boxShadow: SH.card,
                display: "flex", flexDirection: "column", justifyContent: "space-between",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 8,
                    background: bg, display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Svg icon={icon} size={15} col={col} sw={1.8} />
                  </div>
                  {/* Delta change indicator */}
                  <span style={{
                    fontSize: "0.6875rem", fontWeight: 600, fontFamily: '"JetBrains Mono", monospace',
                    color: deltaCol, background: deltaCol === C.green ? C.gLite : C.lite,
                    padding: "2px 6px", borderRadius: 4,
                  }}>{delta}</span>
                </div>
                <div>
                  <Label col={C.ter} mb={4}>{label}</Label>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
                    <span style={{
                      fontFamily: '"JetBrains Mono", monospace',
                      fontSize: "1.875rem", fontWeight: 700, color: col, lineHeight: 1,
                    }}>{val}</span>
                    {unit && <span style={{ fontSize: "0.75rem", color: C.ter, fontWeight: 500 }}>{unit}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Bottom row: Needs Attention + CTA ── */}
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "1.25rem" }}>
          {/* Needs Attention */}
          <div style={{
            background: C.surf, border: `1px solid ${C.bdr}`,
            borderRadius: 14, padding: "1.375rem 1.5rem", boxShadow: SH.card,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: "1.1rem" }}>
              <Svg icon="warn" size={15} col={C.amber} sw={1.8} />
              <h3 style={{ margin: 0, fontSize: "0.9375rem", fontWeight: 600, color: C.text }}>Needs Attention</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {weak.map(({ name, str, s }) => {
                const col = str < 50 ? C.red : C.amber;
                return (
                  <div key={name}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 5 }}>
                      <div>
                        <div style={{ fontSize: "0.8125rem", fontWeight: 500, color: C.text, lineHeight: 1.3 }}>{name}</div>
                        <div style={{ fontSize: "0.6875rem", color: C.ter, marginTop: 2 }}>{s}</div>
                      </div>
                      <span style={{
                        fontFamily: '"JetBrains Mono", monospace',
                        fontSize: "0.8125rem", fontWeight: 700, color: col, flexShrink: 0, marginLeft: 8,
                      }}>{str}%</span>
                    </div>
                    <Bar pct={str} color={col} />
                  </div>
                );
              })}
            </div>
          </div>

          {/* CTA */}
          <div style={{
            background: C.surf, border: `1px solid ${C.bdr}`,
            borderRadius: 14, padding: "1.625rem 1.75rem",
            boxShadow: SH.card, display: "flex", flexDirection: "column",
          }}>
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: "0 0 8px", fontSize: "1.1rem", fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>
                Ready to practise?
              </h3>
              <p style={{ margin: "0 0 16px", fontSize: "0.875rem", color: C.sec, lineHeight: 1.7, maxWidth: 480 }}>
                Ten AI-generated questions, tuned to your weakest topics, at real ESAT difficulty and pace — with instant feedback and full worked solutions.
              </p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {[
                  { icon: "sparkle", label: "AI-generated" },
                  { icon: "clock", label: "~15 minutes" },
                  { icon: "book", label: "Worked solutions" },
                  { icon: "bolt", label: "Keyboard-first" },
                ].map(({ icon, label }) => (
                  <span key={label} style={{
                    display: "inline-flex", alignItems: "center", gap: 5,
                    fontSize: "0.75rem", color: C.mid, fontWeight: 500,
                    background: C.lite, padding: "4px 10px", borderRadius: 20,
                    border: `1px solid ${C.liteb}`,
                  }}>
                    <Svg icon={icon} size={11} col={C.mid} sw={2} />
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: "1.5rem" }}>
              <button onClick={onStart} className="btn-primary" style={{
                flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                padding: "0.75rem 1.25rem",
                borderRadius: 10, border: "none",
                background: C.mid, color: "#fff",
                fontSize: "0.9rem", fontWeight: 600, fontFamily: "Inter, sans-serif",
                letterSpacing: "-0.01em",
              }}>
                <Svg icon="play" size={14} col="#fff" sw={0} fill="#fff" />
                Start Practising
              </button>
              <button className="btn-ghost" style={{
                display: "flex", alignItems: "center", gap: 7,
                padding: "0.75rem 1.125rem",
                borderRadius: 10, border: `1px solid ${C.bdr}`,
                background: C.surf, color: C.sec,
                fontSize: "0.875rem", fontWeight: 500, fontFamily: "Inter, sans-serif",
              }}>
                <Svg icon="pencil" size={14} col={C.sec} sw={1.8} />
                Mock Exam
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
 PRACTICE HUB
═══════════════════════════════════════════════════════════════════ */
function PracticeHub({ onBack }) {
  const [cache, setCache] = useState({});
  const cRef = useRef({});
  const [idx, setIdx] = useState(0);
  const [ans, setAns] = useState({});
  const ansRef = useRef({});
  const [showSoln, setShowSoln] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [secs, setSecs] = useState(88);
  const [ticking, setTicking] = useState(true);
  const timerRef = useRef(null);
  const [subj, setSubj] = useState("Mathematics 1");
  const subjRef = useRef("Mathematics 1");
  const [topicPin, setTopicPin] = useState(null);
  const topicPinRef = useRef(null);
  const [hovOpt, setHovOpt] = useState(null);

  useEffect(() => { subjRef.current = subj; }, [subj]);
  useEffect(() => { topicPinRef.current = topicPin; }, [topicPin]);

  const getTopicFor = (i) => {
    if (topicPinRef.current) return topicPinRef.current;
    const ts = [...(TOPICS[subjRef.current] || [])].sort((a, b) => a.str - b.str);
    return ts[i % ts.length]?.name || "Algebra";
  };

  const loadQ = async (i) => {
    if (cRef.current[i]) return;
    const s = subjRef.current, t = getTopicFor(i), d = DIFF_SEQ[i] || "Medium";
    setLoading(true); setError(null);
    try {
      const q = await genQuestion(s, t, d);
      cRef.current[i] = q;
      setCache(prev => ({ ...prev, [i]: q }));
    } catch {
      setError("This question failed to generate. Check your connection and retry.");
    } finally { setLoading(false); }
  };

  useEffect(() => {
    setShowSoln(false); setShowHint(false); setSecs(88);
    setTicking(!ansRef.current[idx]);
    loadQ(idx);
    if (idx < SESSION - 1) setTimeout(() => loadQ(idx + 1), 800);
  }, [idx]);

  useEffect(() => {
    clearInterval(timerRef.current);
    if (ticking) timerRef.current = setInterval(() => setSecs(s => s > 0 ? s - 1 : 0), 1000);
    return () => clearInterval(timerRef.current);
  }, [ticking]);

  useEffect(() => {
    const h = (e) => {
      if (["SELECT","INPUT","TEXTAREA"].includes(e.target.tagName)) return;
      const k = e.key;
      if ("12345".includes(k)) pick("ABCDE"[+k - 1]);
      if ("abcde".includes(k.toLowerCase())) pick(k.toUpperCase());
      if (k === "h" || k === "H") setShowHint(v => !v);
      if ((k === "s" || k === "S") && ansRef.current[idx]) setShowSoln(v => !v);
      if ((k === "ArrowRight" || k === "Enter") && idx < SESSION - 1) setIdx(i => i + 1);
      if (k === "ArrowLeft" && idx > 0) setIdx(i => i - 1);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [idx]);

  const pick = (letter) => {
    if (ansRef.current[idx]) return;
    ansRef.current[idx] = letter;
    setAns(prev => ({ ...prev, [idx]: letter }));
    setTicking(false); clearInterval(timerRef.current);
  };

  const retry = () => {
    delete cRef.current[idx];
    setCache(prev => { const n = {...prev}; delete n[idx]; return n; });
    setError(null); loadQ(idx);
  };

  const q = cache[idx];
  const chosen = ans[idx];
  const correct = q?.ans?.[0];
  const isRight = !!(chosen && correct && chosen === correct);
  const diff = q?.diff || DIFF_SEQ[idx] || "Medium";
  const topic = q?.topic || getTopicFor(idx);
  const dm = DIFF_META[diff] || { bg: C.alt, col: C.sec, bdr: C.bdr };
  const doneCount = Object.keys(ans).length;
  const rightCount = Object.entries(ans).filter(([i, a]) => a === (cRef.current[+i]?.ans?.[0])).length;
  const urgent = secs <= 20 && ticking && !chosen;
  const tStr = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
  const tCol = chosen ? C.ter : secs > 55 ? C.green : secs > 22 ? C.amber : C.red;

  const optSt = (l) => {
    if (!chosen) {
      return { bg: C.surf, bdr: C.bdr, labelBg: C.alt, textCol: C.text, iconNode: null };
    }
    if (l === correct) return {
      bg: C.gLite, bdr: C.green, labelBg: C.green, textCol: C.green,
      iconNode: <div style={{ width:22, height:22, borderRadius:"50%", background:C.green, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, marginLeft:10 }}>
        <Svg icon="check" size={11} col="#fff" sw={2.5} />
      </div>
    };
    if (l === chosen) return {
      bg: C.rLite, bdr: C.red, labelBg: C.red, textCol: C.red,
      iconNode: <div style={{ width:22, height:22, borderRadius:"50%", background:C.red, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, marginLeft:10 }}>
        <Svg icon="x" size={11} col="#fff" sw={2.5} />
      </div>
    };
    return { bg: C.surf, bdr: C.bdr, labelBg: "#E3E0DA", textCol: C.ter, iconNode: null };
  };

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: C.bg, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <GlobalStyles />

      {/* ── Header ── */}
      <header style={{
        background: C.surf, height: 58, borderBottom: `1px solid ${C.bdr}`,
        display: "flex", alignItems: "center", padding: "0 1.75rem",
        flexShrink: 0, position: "sticky", top: 0, zIndex: 100, gap: 16, overflow: "visible",
      }}>
        <button onClick={onBack} className="btn-ghost" style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "none", border: "none", cursor: "pointer",
          color: C.sec, fontSize: "0.8125rem", fontWeight: 500,
          fontFamily: "Inter, sans-serif", padding: "5px 10px", borderRadius: 7,
        }}>
          <Svg icon="arrowL" size={14} col={C.sec} sw={1.8} />
          Dashboard
        </button>
        <div style={{ width: 1, height: 20, background: C.bdr }} />
        <Wordmark />

        {/* Keyboard shortcuts legend */}
        <div style={{
          marginLeft: "auto",
          display: "flex", alignItems: "center", gap: 8,
          background: C.alt, borderRadius: 8, padding: "5px 10px",
        }}>
          <Svg icon="bolt" size={12} col={C.ter} sw={1.8} />
          {[
            { k: "1–5", label: "Select" },
            { k: "H", label: "Hint" },
            { k: "S", label: "Solution" },
          ].map(({ k, label }, i) => (
            <span key={k} style={{ display:"flex", alignItems:"center", gap:4 }}>
              {i > 0 && <span style={{ color: C.bdr2, fontSize:"0.75rem" }}>·</span>}
              <KBD>{k}</KBD>
              <span style={{ fontSize: "0.6875rem", color: C.ter }}>{label}</span>
            </span>
          ))}
          <span style={{ color: C.bdr2, fontSize:"0.75rem" }}>·</span>
          <KBD>←</KBD>
          <KBD>→</KBD>
          <span style={{ fontSize: "0.6875rem", color: C.ter }}>Navigate</span>
        </div>

        {/* Session progress pill + mini dots */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div style={{ display: "flex", gap: 3 }}>
            {Array.from({ length: SESSION }, (_, i) => {
              const a = ans[i];
              const qd = cRef.current[i];
              const ok = !!(a && qd?.ans?.[0] && a === qd.ans[0]);
              return (
                <div key={i} style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: !a ? (i === idx ? C.mid : C.bdr) : ok ? C.green : C.red,
                  transition: "background 0.25s",
                  opacity: i === idx && !a ? 1 : undefined,
                  boxShadow: i === idx && !a ? `0 0 0 2px ${C.liteb}` : undefined,
                }} />
              );
            })}
          </div>
          <div style={{ fontSize: "0.8125rem", color: C.sec }}>
            <span style={{ fontFamily:'"JetBrains Mono",monospace', fontWeight:700, color:C.text }}>{doneCount}</span>
            <span style={{ color: C.ter }}> / {SESSION}</span>
          </div>
        </div>
        {/* Thin progress stripe at bottom of sticky header */}
        <div style={{ position:"absolute", bottom:0, left:0, right:0, height:2, background:C.bdr }}>
          <div style={{
            height:"100%", borderRadius:1,
            width:`${(doneCount / SESSION) * 100}%`,
            background: doneCount === SESSION ? C.green : C.mid,
            transition:"width 0.45s cubic-bezier(0.16,1,0.3,1), background 0.3s",
          }} />
        </div>
      </header>

      {/* ── Main layout ── */}
      <div style={{
        flex: 1, maxWidth: 1200, width: "100%", margin: "0 auto",
        padding: "1.5rem 1.75rem",
        display: "flex", gap: "1.5rem", boxSizing: "border-box",
      }}>

        {/* ════════════ LEFT: Question pane ════════════ */}
        <div style={{ flex: "1 1 0", minWidth: 0 }}>

          {/* Meta row */}
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:"1rem", flexWrap:"wrap" }}>
            <Pill bg={C.lite} col={C.mid} bdr={C.liteb}>{subj}</Pill>
            <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>{diff}</Pill>
            {topic && <Pill bg={C.alt} col={C.sec} bdr={C.bdr}>{topic}</Pill>}
            <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:8 }}>
              {/* Arc timer — thin circle showing remaining fraction */}
              {(() => {
                const r = 14, cx = 16, cy = 16, stroke = 2;
                const circ = 2 * Math.PI * r;
                const pct = chosen ? 0 : secs / 88;
                const col = chosen ? C.ter : secs > 55 ? C.green : secs > 22 ? C.amber : C.red;
                return (
                  <svg width={32} height={32} viewBox="0 0 32 32" style={{ flexShrink: 0, transform: "rotate(-90deg)" }}>
                    <circle cx={cx} cy={cy} r={r} fill="none" stroke={C.bdr} strokeWidth={stroke} />
                    <circle cx={cx} cy={cy} r={r} fill="none" stroke={col} strokeWidth={stroke}
                      strokeDasharray={circ}
                      strokeDashoffset={circ * (1 - pct)}
                      strokeLinecap="round"
                      style={{ transition: "stroke-dashoffset 1s linear, stroke 0.5s" }}
                    />
                  </svg>
                );
              })()}
              <span className={urgent ? "timer-urgent" : ""} style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: "0.9375rem", fontWeight: 700,
                color: chosen ? C.ter : tCol,
                transition: "color 0.3s",
                letterSpacing: "-0.03em",
                minWidth: 36,
              }}>{tStr}</span>
            </div>
          </div>

          {/* Question navigator */}
          <div style={{ display:"flex", gap:6, marginBottom:"1.25rem", flexWrap:"wrap" }}>
            {Array.from({ length: SESSION }, (_, i) => {
              const a = ans[i];
              const qd = cRef.current[i];
              const ok = !!(a && qd?.ans?.[0] && a === qd.ans[0]);
              const cur = i === idx;
              let bg = C.surf, bdr = C.bdr, col = C.ter;
              if (a) { bg = ok ? C.gLite : C.rLite; bdr = ok ? C.green : C.red; col = ok ? C.green : C.red; }
              if (cur) { bdr = C.mid; }
              return (
                <button key={i} onClick={() => setIdx(i)} className="q-num-btn" style={{
                  width: 36, height: 36, borderRadius: 8,
                  border: `2px solid ${bdr}`, background: bg,
                  color: col,
                  fontFamily: '"JetBrains Mono", monospace',
                  fontWeight: cur ? 700 : 500,
                  fontSize: "0.75rem", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxSizing: "border-box",
                  boxShadow: cur ? `0 0 0 3px ${C.lite}` : "none",
                }}>
                  {a ? (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                      stroke={col} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      {ok
                        ? <path d="M4.5 12.75l6 6 9-13.5" />
                        : <><path d="M6 18 18 6"/><path d="M6 6l12 12"/></>
                      }
                    </svg>
                  ) : i + 1}
                </button>
              );
            })}
          </div>

          {/* Loading */}
          {loading && !q && (
            <div style={{
              background: C.surf,
              border: `1px solid ${C.bdr}`,
              borderLeft: `5px solid ${C.mid}`,
              borderRadius: "0 12px 12px 0",
              padding: "1.5rem 1.75rem",
              display: "flex", alignItems: "center", gap: 12,
              marginBottom: "1rem", boxShadow: SH.card,
            }}>
              <div className="spinner" style={{
                width: 18, height: 18, borderRadius: "50%",
                border: `2.5px solid ${C.lite}`,
                borderTop: `2.5px solid ${C.mid}`,
                flexShrink: 0,
              }} />
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 500, color: C.text, marginBottom: 2 }}>
                  Generating question…
                </div>
                <div style={{ fontSize: "0.75rem", color: C.ter }}>
                  AI is writing a fresh {diff.toLowerCase()} {topic} problem
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              background: C.rLite, border: `1px solid ${C.rBdr}`,
              borderRadius: 12, padding: "1rem 1.25rem", marginBottom: "1rem",
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:7, marginBottom:6 }}>
                <Svg icon="xCir" size={16} col={C.red} sw={1.8} />
                <span style={{ fontWeight: 600, color: C.red, fontSize: "0.875rem" }}>
                  Generation failed
                </span>
              </div>
              <p style={{ margin:"0 0 10px", color:C.red, fontSize:"0.8125rem", opacity:0.85 }}>{error}</p>
              <button onClick={retry} className="btn-primary" style={{
                padding:"5px 12px", borderRadius:7, border:"none",
                background:C.red, color:"#fff",
                fontFamily:"Inter,sans-serif", fontWeight:600, fontSize:"0.8125rem",
              }}>
                Retry
              </button>
            </div>
          )}

          {/* ── Question card — Gymnasium Lane border ── */}
          {q && (
            <div style={{
              background: C.surf,
              borderTop: `1px solid ${C.bdr}`,
              borderRight: `1px solid ${C.bdr}`,
              borderBottom: `1px solid ${C.bdr}`,
              borderLeft: `5px solid ${C.mid}`,
              borderRadius: "0 12px 12px 0",
              padding: "1.5rem 1.75rem",
              marginBottom: "0.875rem",
              boxShadow: SH.card,
            }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"0.875rem" }}>
                <Label col={C.ter}>Question {idx + 1} of {SESSION}</Label>
                <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                  <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>{diff}</Pill>
                </div>
              </div>
              <p style={{
                margin: 0, fontSize: "0.9375rem", lineHeight: 1.85,
                color: C.text, fontWeight: 400,
              }}>
                {q.q || q.question}
              </p>
            </div>
          )}

          {/* ── Answer options ── */}
          {q && (
            <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:"0.875rem" }}>
              {(q.opts || q.options || []).map((opt, i) => {
                const l = "ABCDE"[i];
                const st = optSt(l);
                const isHov = hovOpt === l && !chosen;
                return (
                  <button
                    key={l}
                    onClick={() => pick(l)}
                    onMouseEnter={() => !chosen && setHovOpt(l)}
                    onMouseLeave={() => setHovOpt(null)}
                    className={`opt-btn${chosen ? " answered" : ""}`}
                    disabled={!!chosen}
                    style={{
                      display:"flex", alignItems:"center",
                      padding:"0.75rem 1rem",
                      border:`2px solid ${isHov ? C.mid : st.bdr}`,
                      borderRadius:10,
                      background: isHov ? C.lite : st.bg,
                      fontFamily:"Inter,sans-serif",
                      textAlign:"left", width:"100%", boxSizing:"border-box",
                      cursor: chosen ? "default" : "pointer",
                    }}
                  >
                    {/* Letter badge */}
                    <span style={{
                      width: 28, height: 28, borderRadius: 7, flexShrink: 0,
                      background: chosen ? st.labelBg : isHov ? C.mid : C.alt,
                      color: chosen ? "#fff" : isHov ? "#fff" : C.sec,
                      fontFamily:'"JetBrains Mono",monospace',
                      fontWeight: 700, fontSize: "0.8125rem",
                      display:"flex", alignItems:"center", justifyContent:"center",
                      transition:"background 0.12s, color 0.12s",
                      marginRight: "0.875rem",
                    }}>
                      {l}
                    </span>
                    {/* Text */}
                    <span style={{
                      flex: 1, color: st.textCol, fontSize: "0.875rem", lineHeight: 1.6,
                      fontWeight: chosen && (l === correct || l === chosen) ? 500 : 400,
                    }}>
                      {opt.replace(/^[A-E]\)\s*/, "")}
                    </span>
                    {/* Right indicator */}
                    {st.iconNode}
                  </button>
                );
              })}
            </div>
          )}

          {/* ── Hint panel ── */}
          {q && (
            <div style={{ marginBottom: 8 }}>
              <button
                onClick={() => setShowHint(h => !h)}
                className={`collapse-btn${showHint ? " hint-btn-open" : ""}`}
                style={{
                  display:"flex", alignItems:"center", gap:8,
                  width:"100%", padding:"0.625rem 1rem",
                  borderRadius: showHint ? "9px 9px 0 0" : 9,
                  border:`1px solid ${showHint ? C.aBdr : C.bdr}`,
                  background: showHint ? C.aLite : C.surf,
                  color: showHint ? C.amber : C.sec,
                  fontSize:"0.8125rem", fontWeight:500, fontFamily:"Inter,sans-serif",
                  boxSizing:"border-box", textAlign:"left",
                }}
              >
                <Svg icon="bulb" size={15} col={showHint ? C.amber : C.ter} sw={1.8} />
                <span style={{ flex:1 }}>{showHint ? "Hide hint" : "Reveal hint"}</span>
                <KBD>H</KBD>
              </button>
              {showHint && (
                <div style={{
                  padding:"1rem 1.1rem",
                  background:C.aLite, border:`1px solid ${C.aBdr}`, borderTop:"none",
                  borderRadius:"0 0 9px 9px",
                }}>
                  <p style={{ margin:0, color:C.amber, fontSize:"0.875rem", lineHeight:1.75 }}>
                    {q.hint}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ── Solution panel (post-answer) ── */}
          {chosen && q && (
            <div style={{ marginBottom: 8, marginTop: 2 }}>
              <button
                onClick={() => setShowSoln(s => !s)}
                className={`collapse-btn${showSoln ? " soln-btn-open" : ""}`}
                style={{
                  display:"flex", alignItems:"center", gap:8,
                  width:"100%", padding:"0.625rem 1rem",
                  borderRadius: showSoln ? "9px 9px 0 0" : 9,
                  border:`1px solid ${showSoln ? C.liteb : C.bdr}`,
                  background: showSoln ? C.lite : C.surf,
                  color: showSoln ? C.mid : C.sec,
                  fontSize:"0.8125rem", fontWeight:500, fontFamily:"Inter,sans-serif",
                  boxSizing:"border-box", textAlign:"left",
                }}
              >
                <Svg icon="book" size={15} col={showSoln ? C.mid : C.ter} sw={1.8} />
                <span style={{ flex:1 }}>{showSoln ? "Hide solution" : "Show worked solution"}</span>
                {/* Correctness badge */}
                <span style={{
                  padding:"2px 8px", borderRadius:6,
                  background: isRight ? C.gLite : C.rLite,
                  color: isRight ? C.green : C.red,
                  fontSize:"0.75rem", fontWeight:700,
                  display:"flex", alignItems:"center", gap:4,
                }}>
                  {isRight
                    ? <><Svg icon="check" size={10} col={C.green} sw={2.5} />Correct</>
                    : <><Svg icon="x" size={10} col={C.red} sw={2.5} />Answer: {correct}</>
                  }
                </span>
                <KBD>S</KBD>
              </button>
              {showSoln && (
                <div style={{
                  padding:"1.25rem 1.375rem",
                  background:C.lite, border:`1px solid ${C.liteb}`, borderTop:"none",
                  borderRadius:"0 0 9px 9px",
                }}>
                  <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:"0.75rem" }}>
                    <Svg icon="sparkle" size={14} col={C.mid} sw={1.8} />
                    <span style={{ fontSize:"0.8125rem", fontWeight:600, color:C.blue }}>
                      Worked Solution
                    </span>
                  </div>
                  <p style={{
                    margin:0, color:C.text, fontSize:"0.875rem",
                    lineHeight:1.9, whiteSpace:"pre-wrap",
                  }}>
                    {q.soln || q.solution}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ── Session complete ── */}
          {doneCount === SESSION && (
            <div style={{
              background: C.surf, border: `1px solid ${C.gBdr}`,
              borderRadius: 14, padding: "1.375rem 1.5rem", marginBottom: 8,
              boxShadow: SH.card,
            }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 14, marginBottom: 14 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: C.gLite, border: `1px solid ${C.gBdr}`,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }}>
                  <Svg icon="trophy" size={22} col={C.green} sw={1.5} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, color: C.text, fontSize: "1rem", letterSpacing: "-0.01em", marginBottom: 3 }}>
                    Session complete
                  </div>
                  <div style={{ fontSize: "0.875rem", color: C.sec }}>
                    <span style={{ fontFamily:'"JetBrains Mono",monospace', fontWeight:700, color: rightCount >= 8 ? C.green : rightCount >= 5 ? C.amber : C.red }}>
                      {rightCount}/{SESSION}
                    </span>
                    {" "}correct — {rightCount >= 8 ? "excellent work." : rightCount >= 5 ? "solid session." : "keep practising."}
                  </div>
                </div>
                <button onClick={onBack} className="btn-primary" style={{
                  padding:"8px 16px", borderRadius:8, border:"none",
                  background:C.mid, color:"#fff",
                  fontFamily:"Inter,sans-serif", fontWeight:600, fontSize:"0.8125rem",
                  flexShrink: 0,
                }}>
                  Dashboard
                </button>
              </div>
              {/* Per-question result grid */}
              <div style={{ display: "flex", gap: 5 }}>
                {Array.from({ length: SESSION }, (_, i) => {
                  const a = ans[i];
                  const qd = cRef.current[i];
                  const ok = !!(a && qd?.ans?.[0] && a === qd.ans[0]);
                  return (
                    <div key={i} onClick={() => setIdx(i)} style={{
                      flex: 1, height: 28, borderRadius: 6, cursor: "pointer",
                      background: ok ? C.gLite : C.rLite,
                      border: `1px solid ${ok ? C.gBdr : C.rBdr}`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
                        stroke={ok ? C.green : C.red} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        {ok ? <path d="M4.5 12.75l6 6 9-13.5" /> : <><path d="M6 18 18 6"/><path d="M6 6l12 12"/></>}
                      </svg>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Prev / Next ── */}
          <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:4 }}>
            <button
              onClick={() => idx > 0 && setIdx(i => i - 1)}
              className="nav-btn"
              disabled={idx === 0}
              style={{
                display:"flex", alignItems:"center", gap:6,
                padding:"7px 14px", borderRadius:8,
                border:`1px solid ${C.bdr}`, background:C.surf,
                color: idx === 0 ? C.ter : C.sec,
                fontSize:"0.8125rem", fontWeight:500, fontFamily:"Inter,sans-serif",
                opacity: idx === 0 ? 0.4 : 1, cursor: idx === 0 ? "default" : "pointer",
              }}
            >
              <Svg icon="chevL" size={13} col="currentColor" sw={2} />
              Previous
            </button>
            <button
              onClick={() => idx < SESSION - 1 && setIdx(i => i + 1)}
              className="nav-btn"
              disabled={idx === SESSION - 1}
              style={{
                display:"flex", alignItems:"center", gap:6,
                padding:"7px 14px", borderRadius:8,
                border:`1px solid ${C.bdr}`, background:C.surf,
                color: idx === SESSION - 1 ?