# Style Guide — MATHS2.MM2 (Sequences and series)

- Module: Mathematics 2 (M2)
- Corpus questions classified under this topic: 47
- corpus_backed: True

---

# Style Guide: MATHS2.MM2 (Sequences and Series)

## Question Structure Patterns

Questions in this domain frequently follow one of three structural templates:

1.  **The "Defined by Formula" Template** (20% frequency):
    *   A sequence is defined by an explicit formula or a simple recurrence (e.g., $a_{n+1} = f(a_n)$ or $u_n = pn^2 + q$).
    *   *Task:* Identify the pattern/formula, then calculate a specific term or the sum of a subset of terms.
    *   *Example:* Q3 (Quadratic nth term), Q17 (Recurrence).

2.  **The "Simultaneous Sequence" Template** (60% frequency):
    *   Two properties of a sequence (AP or GP) are given (e.g., $S_{20}=50$, $S_{21-40}=-50$ or $u_3=4, u_5=2$).
    *   *Task:* Solve for the core parameters ($a$ and $d$, or $a$ and $r$).
    *   *Follow-up:* Use these parameters to find a sum to infinity, a specific term, or a sum of a modified series (e.g., even terms only).
    *   *Example:* Q1, Q4, Q5, Q7, Q33.

3.  **The "Series of Functions" Template** (20% frequency):
    *   The series involves trigonometric or logarithmic terms (e.g., $\sum \sin(k\pi/3)$, $\sum \log(3^{1-n})$).
    *   *Task:* Recognize the periodicity or logarithmic property to transform the series into a standard AP or GP.
    *   *Example:* Q35, Q40, Q42.

## Difficulty Calibration

*   **Band 1-3 (Direct Application):**
    *   Standard AP/GP formula usage ($S_n$, $S_\infty$).
    *   Finding $a, d, r$ from given terms.
    *   *Example:* Q15 (Compare linear vs quadratic).
*   **Band 4-6 (Multi-step Reasoning):**
    *   Relating sums of different intervals (e.g., Sum of first 20 vs next 20).
    *   Solving simultaneous equations derived from sequence properties.
    *   Handling conditions like "real and positive" or "convergent".
    *   *Example:* Q4 (Sums of 20s), Q19 (AP relations).
*   **Band 7-9 (Abstract/Compound):**
    *   Sum of squares/cubes of a GP.
    *   Intersecting sequences (e.g., finding the $N$-th common term).
    *   Complex recurrence relations or period identification in trigonometric series.
    *   *Example:* Q26 (Sum of squares), Q27 (Intersecting APs), Q35 (Trig period).

## Wording Conventions

*   **"Real and positive":** Almost exclusively used in Geometric Progression questions to force the selection of a specific root for the common ratio $r$. (Q1, Q14).
*   **"Sum of the first n terms" ($S_n$):** Often used in arithmetic questions involving differences of sums (e.g., $S_{n+1} - S_{n-1}$).
*   **"Successive terms of an arithmetic series":** Used to imply a constant difference condition between geometric terms (e.g., $u_1, u_2, u_4$ form an AP).
*   **"Convergent":** Implies $|r| < 1$ and is a prerequisite for using Sum to Infinity formula.

## Calculator-Free Arithmetic Patterns

*   **Roots:** Questions involving roots (e.g., 5th roots) usually have options that isolate the radical term or simplify the denominator (e.g., $\frac{k \sqrt[n]{x}}{\sqrt[n]{x} \pm 1}$). This avoids heavy calculation.
*   **Modulus:** Questions asking for the "modulus of the difference" (Q5) allow the answer to be positive even if the underlying terms/differences are negative, simplifying the mental check.
*   **Integer Parameters:** In AP questions, $a$ and $d$ are frequently integers or simple fractions to allow simultaneous equations to be solved mentally (e.g., Q21).
*   **Cancellation:** In summations like $\sum \log_{10}(3^{1-n})$, the index shift is designed to utilize the formula $\sum_{k=1}^N k = N(N+1)/2$ where $N=100$, resulting in clean integers like 5050.
