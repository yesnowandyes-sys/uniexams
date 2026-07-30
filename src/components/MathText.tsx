"use client";

import { useMemo } from "react";
import katex from "katex";

/**
 * MathText — renders a string that mixes plain text with LaTeX math.
 *
 * Supported delimiters, scanned left-to-right, non-overlapping:
 *   $$...$$         display math
 *   \[...\]         display math
 *   \(...\)         inline math
 *   $...$           inline math (single-dollar; skipped when adjacent to a digit)
 *
 * KaTeX runs with throwOnError:false, so malformed OCR fragments degrade to
 * a red error node instead of crashing the page.
 *
 * Output is a single HTML string, trusted because every math node goes
 * through katex.renderToString and every text node is HTML-escaped.
 */
type Segment =
  | { kind: "text"; value: string }
  | { kind: "inline"; value: string }
  | { kind: "display"; value: string };

// One alternation pass. Order matters: $$ before $, \[ / \( before raw \.
const TOKEN_RE = new RegExp(
  [
    /\$\$([\s\S]+?)\$\$/.source, // 1: display $$
    /\\\[([\s\S]+?)\\\]/.source, // 2: display \[
    /\\\(([\s\S]+?)\\\)/.source, // 3: inline \(
    /\$(?!\d)([^\$\n]+?)\$(?!\d)/.source, // 4: inline $...$ (not adjacent to digit)
  ].join("|"),
  "g"
);

function tokenize(input: string): Segment[] {
  if (!input) return [];
  const out: Segment[] = [];
  let cursor = 0;
  TOKEN_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = TOKEN_RE.exec(input)) !== null) {
    if (m.index > cursor) {
      out.push({ kind: "text", value: input.slice(cursor, m.index) });
    }
    if (m[1] != null) out.push({ kind: "display", value: m[1] });
    else if (m[2] != null) out.push({ kind: "display", value: m[2] });
    else if (m[3] != null) out.push({ kind: "inline", value: m[3] });
    else if (m[4] != null) out.push({ kind: "inline", value: m[4] });
    cursor = m.index + m[0].length;
    // Guard against zero-length matches looping forever.
    if (m[0].length === 0) TOKEN_RE.lastIndex++;
  }
  if (cursor < input.length) {
    out.push({ kind: "text", value: input.slice(cursor) });
  }
  return out;
}

function renderMath(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex, {
      displayMode,
      throwOnError: false,
      strict: false,
      output: "html",
    });
  } catch {
    return `<span style="color:#DC2626;font-family:monospace">${escapeHtml(tex)}</span>`;
  }
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function MathText({
  children,
  as: Tag = "span",
  style,
  className,
}: {
  children: string;
  as?: "span" | "div" | "p";
  style?: React.CSSProperties;
  className?: string;
}) {
  const segments = useMemo(() => tokenize(children ?? ""), [children]);

  const html = useMemo(() => {
    return segments
      .map((s) => {
        if (s.kind === "text") return escapeHtml(s.value);
        if (s.kind === "inline") return renderMath(s.value, false);
        return renderMath(s.value, true);
      })
      .join("");
  }, [segments]);

  return (
    <Tag
      style={style}
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
