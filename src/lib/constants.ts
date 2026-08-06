/* ═══════════════════════════════════════════════════════════════════
   DESIGN TOKENS
   ═══════════════════════════════════════════════════════════════════ */
export const C = {
  bg: "#F6F5F1",
  surf: "#FFFFFF",
  alt: "#EFECEA",
  bdr: "#E3E0DA",
  bdr2: "#C9C6C0",
  text: "#18181A",
  sec: "#504F4C",
  ter: "#9E9C98",
  blue: "#1A47B8",
  mid: "#2563EB",
  lite: "#EEF4FF",
  liteb: "#DBEAFE",
  green: "#15803D",
  gLite: "#F0FDF4",
  gBdr: "#86EFAC",
  red: "#DC2626",
  rLite: "#FEF2F2",
  rBdr: "#FECACA",
  amber: "#B45309",
  aLite: "#FFFBEB",
  aBdr: "#FDE68A",
  purp: "#7C3AED",
  pLite: "#F5F3FF",
  pBdr: "#DDD6FE",
} as const;

export const SH = {
  card: "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)",
  lifted: "0 3px 10px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)",
  blue: "0 4px 14px rgba(37,99,235,0.22), 0 1px 3px rgba(37,99,235,0.12)",
} as const;

/** Shared accuracy → colour threshold used by the knowledge map and progress bars. */
export function tierColor(v: number): string {
  if (v >= 75) return C.green;
  if (v >= 55) return C.amber;
  if (v > 0) return C.red;
  return C.bdr2;
}

/* ═══════════════════════════════════════════════════════════════════
   CONSTANTS
   ═══════════════════════════════════════════════════════════════════ */
export const EXAM_DATE = new Date("2026-10-09");
export const DAYS_LEFT = Math.max(
  0,
  Math.ceil((EXAM_DATE.getTime() - Date.now()) / 86400000)
);
export const SESSION = 10;

export type TopicStr = { name: string; str: number };

export const TOPICS: Record<string, TopicStr[]> = {
  "Mathematics 1": [
    { name: "Algebra & Polynomials", str: 72 },
    { name: "Sequences & Series", str: 59 },
    { name: "Geometry & Trigonometry", str: 85 },
    { name: "Statistics & Probability", str: 64 },
    { name: "Calculus", str: 57 },
  ],
  Physics: [
    { name: "Mechanics", str: 78 },
    { name: "Electricity & Magnetism", str: 44 },
    { name: "Waves & Optics", str: 67 },
    { name: "Thermodynamics", str: 51 },
    { name: "Modern Physics", str: 63 },
  ],
  Chemistry: [
    { name: "Atomic Structure", str: 86 },
    { name: "Energetics & Kinetics", str: 68 },
    { name: "Organic Chemistry", str: 71 },
    { name: "Equilibrium & Acids", str: 59 },
  ],
  Biology: [
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

export type RadarPoint = { axis: string; v: number };

export const RADAR_DATA: RadarPoint[] = [
  { axis: "Maths 1", v: 67 },
  { axis: "Physics", v: 61 },
  { axis: "Chemistry", v: 71 },
  { axis: "Biology", v: 79 },
  { axis: "Maths 2", v: 50 },
];

export type DiffKey = "Easy" | "Medium" | "Hard" | "Very Hard";

export const DIFF_META: Record<DiffKey, { bg: string; col: string; bdr: string }> = {
  Easy: { bg: "#F0FDF4", col: "#15803D", bdr: "#86EFAC" },
  Medium: { bg: "#FFFBEB", col: "#B45309", bdr: "#FDE68A" },
  Hard: { bg: "#FEF2F2", col: "#DC2626", bdr: "#FECACA" },
  "Very Hard": { bg: "#F5F3FF", col: "#7C3AED", bdr: "#DDD6FE" },
};

export const DIFF_SEQ: DiffKey[] = [
  "Easy",
  "Medium",
  "Medium",
  "Hard",
  "Medium",
  "Hard",
  "Hard",
  "Very Hard",
  "Medium",
  "Very Hard",
];

/* ═══════════════════════════════════════════════════════════════════
   MOCK QUESTIONS — hardcoded sample data
   ═══════════════════════════════════════════════════════════════════ */
export type Question = {
  q: string;
  opts: string[];
  ans: string;
  topic: string;
  diff: DiffKey;
  hint: string;
  soln: string;
};

export const MOCK_QUESTIONS: Question[] = [
  {
    q: "A polynomial f(x) = x\u00B3 + ax\u00B2 + bx + 6 has roots 1, 2, and 3. What is the value of a?",
    opts: ["A) \u22126", "B) 6", "C) \u22121", "D) 11", "E) \u221211"],
    ans: "A",
    topic: "Algebra & Polynomials",
    diff: "Easy",
    hint: "Use Vieta's formulas: the sum of the roots equals \u2212a/x\u00B3 coefficient.",
    soln: "By Vieta's formulas, the sum of the roots = \u2212a/1.\n\nSum of roots = 1 + 2 + 3 = 6.\n\nSo \u2212a = 6, which gives a = \u22126.\n\nTo verify: (x\u22121)(x\u22122)(x\u22123) = x\u00B3 \u2212 6x\u00B2 + 11x \u2212 6.\nSo a = \u22126. Confirmed.",
  },
  {
    q: "The sum of the first n terms of an arithmetic sequence is Sn = n\u00B2 + 2n. What is the common difference?",
    opts: ["A) 1", "B) 2", "C) 3", "D) 4", "E) n"],
    ans: "B",
    topic: "Sequences & Series",
    diff: "Medium",
    hint: "Find the general term an = Sn \u2212 Sn\u22121, then identify the common difference.",
    soln: "Sn = n\u00B2 + 2n\nSn\u22121 = (n\u22121)\u00B2 + 2(n\u22121) = n\u00B2 \u2212 2n + 1 + 2n \u2212 2 = n\u00B2 \u2212 1\n\nan = Sn \u2212 Sn\u22121 = (n\u00B2 + 2n) \u2212 (n\u00B2 \u2212 1) = 2n + 1\n\nan = 2n + 1, so a1 = 3, a2 = 5, a3 = 7...\n\nCommon difference d = a2 \u2212 a1 = 5 \u2212 3 = 2.",
  },
  {
    q: "In triangle ABC, angle A = 60\u00B0, side b = 8, side c = 5. What is the length of side a?",
    opts: ["A) 6", "B) 7", "C) \u221A39", "D) \u221A49", "E) \u221A89"],
    ans: "B",
    topic: "Geometry & Trigonometry",
    diff: "Medium",
    hint: "Apply the cosine rule: a\u00B2 = b\u00B2 + c\u00B2 \u2212 2bc\u00B7cos(A).",
    soln: "By the cosine rule:\n\na\u00B2 = b\u00B2 + c\u00B2 \u2212 2bc\u00B7cos(A)\na\u00B2 = 8\u00B2 + 5\u00B2 \u2212 2(8)(5)cos(60\u00B0)\na\u00B2 = 64 + 25 \u2212 80(0.5)\na\u00B2 = 89 \u2212 40\na\u00B2 = 49\na = 7",
  },
  {
    q: "A fair six-sided die is rolled twice. What is the probability that the sum of the two rolls is exactly 7?",
    opts: ["A) 1/12", "B) 1/9", "C) 1/6", "D) 5/36", "E) 7/36"],
    ans: "C",
    topic: "Statistics & Probability",
    diff: "Easy",
    hint: "Count the number of ways to get a sum of 7 from two dice.",
    soln: "Total outcomes: 6 \u00D7 6 = 36.\n\nFavourable pairs (sum = 7):\n(1,6), (2,5), (3,4), (4,3), (5,2), (6,1) = 6 ways.\n\nP(sum = 7) = 6/36 = 1/6.",
  },
  {
    q: "Evaluate: \u222B\u2080\u00B9 (3x\u00B2 \u2212 2x + 1) dx",
    opts: ["A) 0", "B) 1", "C) 2", "D) 3", "E) 1.5"],
    ans: "B",
    topic: "Calculus",
    diff: "Medium",
    hint: "Integrate term by term, then evaluate at the bounds.",
    soln: "\u222B(3x\u00B2 \u2212 2x + 1) dx = x\u00B3 \u2212 x\u00B2 + x + C\n\nEvaluate from 0 to 1:\n= [1\u00B3 \u2212 1\u00B2 + 1] \u2212 [0\u00B3 \u2212 0\u00B2 + 0]\n= [1 \u2212 1 + 1] \u2212 0\n= 1",
  },
  {
    q: "A car accelerates uniformly from rest to 20 m/s in 5 seconds. What distance does it travel in this time?",
    opts: ["A) 25 m", "B) 50 m", "C) 75 m", "D) 100 m", "E) 10 m"],
    ans: "B",
    topic: "Mechanics",
    diff: "Easy",
    hint: "Use s = \xBD \u00D7 a \u00D7 t\u00B2 or s = \xBD(u + v)t.",
    soln: "Using s = \xBD(u + v)t:\n\ns = \xBD(0 + 20)(5)\ns = \xBD(20)(5)\ns = 50 m\n\nAlternatively: a = (20\u22120)/5 = 4 m/s\u00B2\ns = \xBD(4)(25) = 50 m.",
  },
  {
    q: "Two resistors of 6\u03A9 and 3\u03A9 are connected in parallel. What is the equivalent resistance?",
    opts: ["A) 9\u03A9", "B) 3\u03A9", "C) 2\u03A9", "D) 4.5\u03A9", "E) 18\u03A9"],
    ans: "C",
    topic: "Electricity & Magnetism",
    diff: "Hard",
    hint: "For parallel resistors: 1/R = 1/R\u2081 + 1/R\u2082.",
    soln: "For parallel resistors:\n\n1/R = 1/R\u2081 + 1/R\u2082\n1/R = 1/6 + 1/3\n1/R = 1/6 + 2/6\n1/R = 3/6 = 1/2\nR = 2\u03A9",
  },
  {
    q: "A sound wave has frequency 680 Hz and speed 340 m/s. What is its wavelength?",
    opts: ["A) 0.25 m", "B) 0.5 m", "C) 1.0 m", "D) 2.0 m", "E) 0.68 m"],
    ans: "B",
    topic: "Waves & Optics",
    diff: "Hard",
    hint: "Use the wave equation: v = f\u03BB.",
    soln: "v = f\u03BB\n\n\u03BB = v/f\n\u03BB = 340/680\n\u03BB = 0.5 m",
  },
  {
    q: "An ideal gas at pressure P and volume V undergoes isothermal expansion to volume 2V. What is the new pressure?",
    opts: ["A) P/2", "B) 2P", "C) P", "D) P/4", "E) 4P"],
    ans: "A",
    topic: "Thermodynamics",
    diff: "Medium",
    hint: "For isothermal processes, PV = constant (Boyle's Law).",
    soln: "For an isothermal process, PV = constant (Boyle's Law).\n\nP\u2081V\u2081 = P\u2082V\u2082\nP \u00B7 V = P\u2082 \u00B7 2V\nP\u2082 = PV / 2V\nP\u2082 = P/2",
  },
  {
    q: "In a hydrogen atom, an electron transitions from n=3 to n=1. The energy of the emitted photon is approximately:",
    opts: [
      "A) 1.89 eV",
      "B) 10.2 eV",
      "C) 12.09 eV",
      "D) 13.6 eV",
      "E) 3.4 eV",
    ],
    ans: "C",
    topic: "Modern Physics",
    diff: "Very Hard",
    hint: "Use En = \u221213.6/n\u00B2 eV and find \u0394E = E\u2083 \u2212 E\u2081.",
    soln: "E_n = \u221213.6/n\u00B2 eV\n\nE\u2083 = \u221213.6/9 = \u22121.51 eV\nE\u2081 = \u221213.6/1 = \u221213.6 eV\n\n\u0394E = E\u2083 \u2212 E\u2081 = \u22121.51 \u2212 (\u221213.6) = 12.09 eV\n\nThe photon carries away this energy.",
  },
];
