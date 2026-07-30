# Style Guide — MATHS2.MM4 (Trigonometry)

- Module: Mathematics 2 (M2)
- Corpus questions classified under this topic: 36
- corpus_backed: True

---

## Question Structure & Difficulty Calibration

*   **Multi-Stage Logic:**
    *   **Pattern:** Questions rarely test a single isolated fact. They typically follow a "Transformation -> Identity Application -> Domain Constraint" path.
    *   **Example:** *Q3 (ENGAA 2019)* requires knowing $\tan x = \sin x / \cos x$ AND rewriting $\sin x / \cos x \times \sin x$ as $\sin^2 x / \cos x$ AND expressing $\sin^2 x$ as $1-\cos^2 x$ to form a solvable quadratic in $\cos x$.
    *   **Difficulty:** Band 4-6. The barrier is algebraic manipulation stamina rather than high-level concept novelty.

*   **Visual-Deception:**
    *   **Pattern:** Questions describe transformations (Stretch/Translate) that map the graph of $y=\sin x$ to a new location.
    *   **Specifics:** "Stretched by scale factor $1/2$ parallel to x-axis" (changes $\omega$ from 1 to 2) is often confused with the argument of the function.
    *   **Example:** *Q2 (ENGAA 2017)* tests the order of operations: $y=\sin(2(x+\pi/4))$ vs $y=\sin(2x+\pi/4)$.

*   **Counting Solutions:**
    *   **Pattern:** A dominant sub-type. The prompt asks for "How many solutions" in $[-2\pi, 2\pi]$ or similar large intervals.
    *   **Calibration:**
        *   Easy: Simple equations ($\sin x = 0.5$) with a visible graph or clear period.
        *   Medium: Compound equations ($\sin 2x = \cos x$) or equations with extraneous roots.
        *   Hard: Inequalities or strict domain constraints involving $p$ or $c$ parameters (*Q34 TMUA 2023*).

*   **"Aha!" Variable Geometry:**
    *   **Pattern:** Using the range of sine/cosine ($[-1, 1]$) as a boundary condition for an otherwise algebraic variable.
    *   **Example:** *Q26 (TMUA 2021)* $(x+1)(3-x) = 2(1-\cos(\pi x))$. The RHS is in $[0, 4]$. The LHS is a quadratic. The overlap defines the solution domain. This connects "Function Analysis" to "Trigonometry".

## Wording Conventions

*   **Ambiguity in Ranges:**
    *   The standard notation $0 \le x \le k$ vs $0 < x < k$ is strict.
    *   "Smallest positive value" is a common trigger (*Q1, Q16*).
    *   "In the range $0^\circ \le x \le 360^\circ$" is the standard default for "find the solutions".
*   **"It is given that...":**
    *   Often precedes a complicated identity like *Q12* ($7\cos x + \tan x \sin x = 5$) to signal that algebraic reduction is the primary task.
*   **"A student gave the following answer...":**
    *   Signals a "Logic/Proof" question (very common in TMUA, rare in ENGAA). Requires checking lines of reasoning rather than calculating from scratch.

## Calculator-Free Arithmetic

*   **Exact Values:**
    *   Expect $\sin$ and $\cos$ of $0, 30, 45, 60, 90$ degrees ($0, \pi/6, \pi/4, \pi/3, \pi/2$).
    *   Students must know $\sin 30^\circ = 1/2$, $\tan 45^\circ = 1$, etc., without aid.
*   **Surds:**
    *   Answers frequently involve $\sqrt{2}$ and $\sqrt{3}$.
    *   *Q3* options include $\sqrt{3}$ or $2\sqrt{2}$.
    *   Rationalizing denominators or simplifying $\sqrt{12} \to 2\sqrt{3}$ is part of the process.
*   **Coefficients:**
    *   Coefficients in equations are often integers or simple fractions ($1/2$, $3/4$) to keep the "number of solutions" integer-based.
    *   *Q35* has coefficients $1, 3, 3$.
    *   *Q8* uses boundaries of $1$ and $0.5$ for $\tan x$ and $\sin 2x$.
