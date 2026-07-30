"use client";

import { CSSProperties, useMemo } from "react";
import type { Question as DbQuestion, Enrichment } from "@/lib/db";
import { C, SH, DIFF_META, type DiffKey } from "@/lib/constants";
import { Svg } from "@/components/icons";
import { Pill, KBD, Label } from "@/components/atoms";
import { QuestionCard } from "@/components/QuestionCard";
import { MathText } from "@/components/MathText";

/**
 * QuestionView — the Practice Hub question renderer (ESA-8).
 *
 * Renders a single real question from the database:
 *   - Gymnasium Lane (5px blue left border) via <QuestionCard>
 *   - Question text with inline/display LaTeX via <MathText>
 *   - Question images (DB question_images[]) served through /api/corpus/
 *   - Dynamic option list (DB has 3–11 options; letters A onward)
 *   - Letter badges, hover state, locked selection after answer
 *   - Worked-solution panel from enrichment.markdown or explanation fallback
 *
 * Stateless beyond what the parent passes in — the page owns session state.
 */

const LETTERS = "ABCDEFGHIJ";

function normDifficulty(d: string | undefined): DiffKey {
  if (!d) return "Medium";
  const k = d.toLowerCase();
  if (k.startsWith("easy")) return "Easy";
  if (k.startsWith("very")) return "Very Hard";
  if (k.startsWith("hard")) return "Hard";
  return "Medium";
}

function deriveSubject(q: DbQuestion): string {
  if (q.subject) return pretty(q.subject);
  if (q.module) return pretty(q.module);
  return pretty(q.exam_type);
}

function pretty(s: string): string {
  // "maths1" -> "Maths 1", "nsaa_s2" -> "NSAA S2", "biology" -> "Biology"
  const parts = s.replace(/_/g, " ").split(/\s+/);
  return parts
    .map((p) => {
      if (/^\d+$/.test(p)) return p;
      // Split trailing digits: "maths1" -> "maths 1"
      const m = p.match(/^([a-zA-Z]+)(\d+)$/);
      if (m) return m[1].charAt(0).toUpperCase() + m[1].slice(1) + " " + m[2];
      return p.charAt(0).toUpperCase() + p.slice(1);
    })
    .join(" ")
    .replace(/\bNsa a\b/i, "NSAA")
    .replace(/\bTmua\b/i, "TMUA")
    .replace(/\bEngaa\b/i, "ENGAA")
    .replace(/\bEsat\b/i, "ESAT");
}

function imageUrl(filename: string): string {
  // Bare filenames in question_images[] are rooted at corpus/images/.
  // Subpaths (e.g. "tmua/x.png" or "esat_screenshots/...") pass through.
  const enc = filename.split("/").map(encodeURIComponent).join("/");
  return filename.includes("/")
    ? `/api/corpus/${enc}`
    : `/api/corpus/images/${enc}`;
}

function optionState(
  letter: string,
  chosen: string | null,
  correct: string
) {
  if (!chosen) {
    return {
      bg: C.surf,
      bdr: C.bdr,
      labelBg: C.alt,
      textCol: C.text,
      iconNode: null as React.ReactNode,
    };
  }
  if (letter === correct) {
    return {
      bg: C.gLite,
      bdr: C.green,
      labelBg: C.green,
      textCol: C.green,
      iconNode: <CheckBadge color={C.green} icon="check" />,
    };
  }
  if (letter === chosen) {
    return {
      bg: C.rLite,
      bdr: C.red,
      labelBg: C.red,
      textCol: C.red,
      iconNode: <CheckBadge color={C.red} icon="x" />,
    };
  }
  return {
    bg: C.surf,
    bdr: C.bdr,
    labelBg: "#E3E0DA",
    textCol: C.ter,
    iconNode: null as React.ReactNode,
  };
}

function CheckBadge({ color, icon }: { color: string; icon: "check" | "x" }) {
  return (
    <div
      style={{
        width: 22,
        height: 22,
        borderRadius: "50%",
        background: color,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginLeft: 10,
      }}
    >
      <Svg icon={icon} size={11} col="#fff" sw={2.5} />
    </div>
  );
}

/** Split enrichment markdown into blocks, render each through MathText. */
function MarkdownWithMath({ source }: { source: string }) {
  const blocks = useMemo(() => splitMarkdown(source), [source]);
  return (
    <>
      {blocks.map((b, i) => (
        <MathText
          key={i}
          as={b.kind === "display" ? "div" : "p"}
          style={{
            margin: b.kind === "display" ? "0.6rem 0" : "0 0 0.5rem 0",
            color: C.text,
            fontSize: "0.875rem",
            lineHeight: 1.9,
            whiteSpace: "pre-wrap",
          }}
        >
          {b.text}
        </MathText>
      ))}
    </>
  );
}

type MdBlock = { kind: "text" | "display"; text: string };

function splitMarkdown(src: string): MdBlock[] {
  // Pull $$...$$ and \[...\] out as display blocks; keep everything else as
  // paragraph text (markdown structure is preserved as plain text — we don't
  // render bold/lists/headings today, only math).
  if (!src) return [];
  const out: MdBlock[] = [];
  const re = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) {
      const t = src.slice(last, m.index).replace(/^\n+|\n+$/g, "");
      if (t) out.push({ kind: "text", text: t });
    }
    const math = m[1] ?? m[2] ?? "";
    out.push({ kind: "display", text: math });
    last = m.index + m[0].length;
  }
  if (last < src.length) {
    const t = src.slice(last).replace(/^\n+|\n+$/g, "");
    if (t) out.push({ kind: "text", text: t });
  }
  return out;
}

function getSolutionText(q: DbQuestion): { source: string; from: "enrichment" | "explanation" | null } {
  const enr: Enrichment | null = q.enrichment;
  if (enr && enr.markdown && enr.markdown.trim()) {
    return { source: enr.markdown, from: "enrichment" };
  }
  if (q.explanation && q.explanation.trim()) {
    return { source: q.explanation, from: "explanation" };
  }
  return { source: "", from: null };
}

export interface QuestionViewProps {
  question: DbQuestion;
  index: number; // 0-based position in session
  total: number; // session size
  chosen: string | null;
  onChoose: (letter: string) => void;
  showSolution: boolean;
  onToggleSolution: (next: boolean) => void;
  hovOpt: string | null;
  onHoverOption: (letter: string | null) => void;
  style?: CSSProperties;
}

export function QuestionView({
  question,
  index,
  total,
  chosen,
  onChoose,
  showSolution,
  onToggleSolution,
  hovOpt,
  onHoverOption,
  style,
}: QuestionViewProps) {
  const diff = normDifficulty(question.enrichment?.difficulty);
  const dm = DIFF_META[diff];
  const subject = deriveSubject(question);
  const topic = question.enrichment?.topics?.[0];
  const optionLetters = Object.keys(question.options).sort();
  const correct = question.correct_answer;
  const isRight = !!(chosen && chosen === correct);
  const solution = getSolutionText(question);

  return (
    <div style={style}>
      {/* Meta row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <Pill bg={C.lite} col={C.mid} bdr={C.liteb}>
          {subject}
        </Pill>
        <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>
          {diff}
        </Pill>
        {topic && (
          <Pill bg={C.alt} col={C.sec} bdr={C.bdr}>
            {topic}
          </Pill>
        )}
        {question.year && (
          <Pill bg={C.alt} col={C.ter} bdr={C.bdr}>
            {question.year}
          </Pill>
        )}
        <div
          style={{
            marginLeft: "auto",
            fontSize: "0.75rem",
            color: C.ter,
            fontFamily: '"JetBrains Mono", monospace',
          }}
        >
          {question.id}
        </div>
      </div>

      {/* ── Question card (Gymnasium Lane) ── */}
      <QuestionCard style={{ marginBottom: "0.875rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.875rem",
          }}
        >
          <Label col={C.ter}>
            Question {index + 1} of {total}
          </Label>
          <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>
            {diff}
          </Pill>
        </div>
        <MathText
          as="p"
          style={{
            margin: 0,
            fontSize: "0.9375rem",
            lineHeight: 1.85,
            color: C.text,
            fontWeight: 400,
          }}
        >
          {question.question_text}
        </MathText>

        {/* Question images */}
        {question.question_images.length > 0 && (
          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
              alignItems: "flex-start",
            }}
          >
            {question.question_images.map((img) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={img}
                src={imageUrl(img)}
                alt={img}
                style={{
                  maxWidth: "100%",
                  borderRadius: 8,
                  border: `1px solid ${C.bdr}`,
                  background: C.surf,
                }}
                loading="lazy"
              />
            ))}
          </div>
        )}
      </QuestionCard>

      {/* ── Answer options ── */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginBottom: "0.875rem",
        }}
      >
        {optionLetters.map((l, i) => {
          const st = optionState(l, chosen, correct);
          const isHov = hovOpt === l && !chosen;
          const text = question.options[l] ?? "";
          return (
            <button
              key={l}
              onClick={() => onChoose(l)}
              onMouseEnter={() => !chosen && onHoverOption(l)}
              onMouseLeave={() => onHoverOption(null)}
              className={`opt-btn${chosen ? " answered" : ""}`}
              disabled={!!chosen}
              style={{
                display: "flex",
                alignItems: "center",
                padding: "0.75rem 1rem",
                border: `2px solid ${isHov ? C.mid : st.bdr}`,
                borderRadius: 10,
                background: isHov ? C.lite : st.bg,
                fontFamily: "Inter,sans-serif",
                textAlign: "left",
                width: "100%",
                boxSizing: "border-box",
                cursor: chosen ? "default" : "pointer",
              }}
            >
              <span
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 7,
                  flexShrink: 0,
                  background: chosen ? st.labelBg : isHov ? C.mid : C.alt,
                  color: chosen ? "#fff" : isHov ? "#fff" : C.sec,
                  fontFamily: '"JetBrains Mono",monospace',
                  fontWeight: 700,
                  fontSize: "0.8125rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "background 0.12s, color 0.12s",
                  marginRight: "0.875rem",
                }}
              >
                {l}
              </span>
              <span
                style={{
                  flex: 1,
                  color: st.textCol,
                  fontSize: "0.875rem",
                  lineHeight: 1.6,
                  fontWeight:
                    chosen && (l === correct || l === chosen) ? 500 : 400,
                }}
              >
                {/* Option text may itself contain math (e.g. "g(\cos 20^\circ)"). */}
                <MathText>{text}</MathText>
                {i < 9 && !chosen && (
                  <span
                    style={{
                      marginLeft: 8,
                      opacity: 0.45,
                      fontSize: "0.6875rem",
                      fontFamily: '"JetBrains Mono",monospace',
                    }}
                  >
                    [{i + 1}]
                  </span>
                )}
              </span>
              {st.iconNode}
            </button>
          );
        })}
      </div>

      {/* ── Solution panel (post-answer) ── */}
      {chosen && (
        <div style={{ marginBottom: 8, marginTop: 2 }}>
          <button
            onClick={() => onToggleSolution(!showSolution)}
            className={`collapse-btn${showSolution ? " soln-btn-open" : ""}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              width: "100%",
              padding: "0.625rem 1rem",
              borderRadius: showSolution ? "9px 9px 0 0" : 9,
              border: `1px solid ${showSolution ? C.liteb : C.bdr}`,
              background: showSolution ? C.lite : C.surf,
              color: showSolution ? C.mid : C.sec,
              fontSize: "0.8125rem",
              fontWeight: 500,
              fontFamily: "Inter,sans-serif",
              boxSizing: "border-box",
              textAlign: "left",
            }}
          >
            <Svg icon="book" size={15} col={showSolution ? C.mid : C.ter} sw={1.8} />
            <span style={{ flex: 1 }}>
              {showSolution ? "Hide worked solution" : "Show worked solution"}
            </span>
            <span
              style={{
                padding: "2px 8px",
                borderRadius: 6,
                background: isRight ? C.gLite : C.rLite,
                color: isRight ? C.green : C.red,
                fontSize: "0.75rem",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              {isRight ? (
                <>
                  <Svg icon="check" size={10} col={C.green} sw={2.5} />
                  Correct
                </>
              ) : (
                <>
                  <Svg icon="x" size={10} col={C.red} sw={2.5} />
                  Answer: {correct}
                </>
              )}
            </span>
            <KBD>S</KBD>
          </button>
          {showSolution && (
            <div
              style={{
                padding: "1.25rem 1.375rem",
                background: C.lite,
                border: `1px solid ${C.liteb}`,
                borderTop: "none",
                borderRadius: "0 0 9px 9px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: "0.75rem",
                }}
              >
                <Svg icon="sparkle" size={14} col={C.mid} sw={1.8} />
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: C.blue }}>
                  Worked Solution
                </span>
                {solution.from === "explanation" && (
                  <span style={{ fontSize: "0.6875rem", color: C.ter }}>
                    (concise)
                  </span>
                )}
              </div>
              {solution.source ? (
                solution.from === "enrichment" ? (
                  <MarkdownWithMath source={solution.source} />
                ) : (
                  <MathText
                    as="p"
                    style={{
                      margin: 0,
                      color: C.text,
                      fontSize: "0.875rem",
                      lineHeight: 1.9,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {solution.source}
                  </MathText>
                )
              ) : (
                <p
                  style={{
                    margin: 0,
                    color: C.ter,
                    fontSize: "0.8125rem",
                    lineHeight: 1.7,
                    fontStyle: "italic",
                  }}
                >
                  Worked solution pending enrichment (see ESA-9). You answered{" "}
                  <strong style={{ color: isRight ? C.green : C.red }}>
                    {chosen}
                  </strong>
                  ; correct answer is{" "}
                  <strong style={{ color: C.green }}>{correct}</strong>.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
