import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Base
        bg: "#F6F5F1",
        surf: "#FFFFFF",
        alt: "#EFECEA",
        bdr: "#E3E0DA",
        bdr2: "#C9C6C0",
        text: "#18181A",
        sec: "#504F4C",
        ter: "#9E9C98",
        // Brand Blue
        blue: "#1A47B8",
        mid: "#2563EB",
        lite: "#EEF4FF",
        liteb: "#DBEAFE",
        // Semantic
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
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        serif: ['"Instrument Serif"', "serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)",
        lifted: "0 3px 10px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)",
        blue: "0 4px 14px rgba(37,99,235,0.22), 0 1px 3px rgba(37,99,235,0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
