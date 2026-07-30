# Style Guide — MATHS2.MM6 (Differentiation)

- Module: Mathematics 2 (M2)
- Corpus questions classified under this topic: 55
- corpus_backed: True

---

# ESAT Topic MATHS2.MM6: Differentiation — Style Guide

## 1. Question Structure & Patterns
The ESAT/TMUA/ENGAA corpus for Differentiation (MM6) focuses heavily on **application and interpretation** rather than rote differentiation of isolated terms. Questions follow distinct macro-patterns:

*   **The "Investigation" Pattern (TMUA style):** Presents a theorem, definition, or "student's working" and asks for validity or errors (e.g., Q44, Q47, Q31). These test the logic of calculus (FTC, Rolle's Theorem, definitions of increasing functions).
*   **The "Geometry-Optimization" Pattern:** Embeds calculus into a physical context (Area of cuboid Q9, Sector of circle Q15, Rectangle in curve Q14, Triangle area Q5).
    *   *Sub-type:* **Implicit/Function Maximization:** Given a curve $y=f(x)$, find the max area of an inscribed shape. Requires setting up the area function $A(x)$ based on the curve's geometry, then differentiating.
*   **The "Parameter Analysis" Pattern:** Gives a polynomial $f(x)$ with parameters (e.g., $a, b, p$) and conditions about roots, stationary points, or tangency. The student solves for the parameter (Q4, Q10, Q25, Q32).
*   **The "Derivative Manipulation" Pattern:** Focuses on algebraic fluency. Given a complex algebraic fraction or root expression, find the derivative at a point (Q13, Q19, Q30, Q38, Q43). These test the ability to simplify $f(x)$ into a sum of powers of $x$ *before* differentiating.

## 2. Difficulty Calibration
Difficulty in this topic is not primarily determined by the complexity of the differentiation rule (only polynomials/powers are used), but by:

1.  **Algebraic Load:**
    *   *Easy:* $x^n \to nx^{n-1}$ with integer $n$.
    *   *Medium:* Fractional powers ($x^{3/2}$), Negative powers, or simple roots ($1/\sqrt{x}$).
    *   *Hard:* Rational functions with roots in the denominator requiring index law manipulation (e.g., rewriting $\frac{x^3-4x}{2\sqrt{x}}$ as $\frac{1}{2}x^{2.5} - 2x^{0.5}$).
2.  **Abstraction Level:**
    *   *Easy:* Find gradient at $x=a$.
    *   *Medium:* Find the range of $k$ such that $f(x)=k$ has $n$ roots.
    *   *Hard:* Determine the truth value of logical statements involving derivatives without explicit functions (e.g., Q40, Q42).
3.  **Multi-step Reasoning:**
    *   *Hard:* Questions requiring "Gradient of the gradient" (e.g., finding max gradient requires finding where $f''(x)=0$ and checking $f'''(x)$).

## 3. Wording Conventions
*   **Strict Definitions:**
    *   "Increasing function" is almost always defined strictly ($f'(x) > 0$).
    *   "Stationary points" implies turning points (Max/Min), not inflection points (horizontal or otherwise).
    *   "Tangent" implies equality of function values ($y_1=y_2$) and derivatives ($m_1=m_2$).
*   **"Complete Set of Values":** Used in inequality questions (Q1, Q3, Q11, Q34). Requires careful attention to open/closed intervals.
*   **"Coefficient of $x^k$":** Common in questions involving derivatives of expansions (Q6). Requires finding the specific term in the derivative polynomial.

## 4. Calculator-Free Arithmetic Patterns
Since these are non-calculator tests:
*   **Surd Answers:** Optimization of geometrical shapes often results in answers involving $\sqrt{2}, \sqrt{3}, \sqrt{6}$ (Q5, Q14).
*   **Fractional Coefficients:** Look for answers like $\frac{9}{4}$ or $\frac{7}{5}$ (Q17, Q23) arising from power rule coefficients ($n/2$).
*   **Integer Roots:** Polynomials are designed to have rational/integer roots to allow factorization to find stationary points.
*   **"Nice" Numbers:** In $y = ax^n + \dots$, the evaluation point $x$ is often chosen to cancel denominators or simplify radicals (e.g., evaluating at $x=4$ for functions of $\sqrt{x}$).

## 5. Scope Constraints (Based on Spec)
*   **Allowed:** $x^n$ for rational $n$, Sums/Differences, Simplification required (e.g. $(2+3x)^6$ expansion or algebraic fractions).
*   **Explicitly Excluded (per spec):** Trig differentiation, Chain Rule, Product Rule, Quotient Rule as formal methods.
    *   *Note:* Questions like Q6 ($(2+3x)^6$) or Q30/38 (algebraic fractions) appear in the corpus. The solution path invariably involves **algebraic expansion or simplification into polynomial form** followed by term-by-term differentiation. Students attempting to apply formal Chain/Product rules will likely run out of time or complexity.
