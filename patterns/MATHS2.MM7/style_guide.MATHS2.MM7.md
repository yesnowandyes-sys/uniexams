# Style Guide — MATHS2.MM7 (Integration)

- Module: Mathematics 2 (M2)
- Corpus questions classified under this topic: 48
- corpus_backed: True

---

# ESAT Mathematics 2 (MM7 Integration) Style Guide

## 1. Question Structure & Format
*   **Context Split:**
    *   **Pure Math (60%):** Focuses on areas between curves, properties of definite integrals, and Trapezium Rule estimation.
        *   *Example:* "The curve C has equation $y = 9 - x^2$. The line L has equation $y = 5$. What is the area enclosed between C and L?" (Q2)
    *   **Applied Context (40%):** Uses kinematics (acceleration/velocity) to frame integration problems.
        *   *Example:* "A car accelerates... $a = 4.0 - 0.36t$... What is its displacement?" (Q8)
*   **Modality:** Questions are rarely "Calculate this integral" in isolation. They usually ask for:
    *   The value of a coefficient in an expansion (Q6).
    *   The value of an unknown limit $m$ (Q4).
    *   Areas between curves (requiring integration setup).
    *   Properties of integrals (inequalities, symmetry).

## 2. Difficulty Calibration
*   **Band 1-3 (Foundation):** Direct application of $\int x^n$.
    *   *Calc:* Simple algebraic expansion (e.g., $(1/\sqrt{x} + \sqrt{x})^2$) followed by basic integration (Q44).
*   **Band 4-6 (Core):** Multi-step reasoning involving areas.
    *   *Setup:* Finding intersection points, then integrating the difference $Top - Bottom$.
    *   *Trap:* Recognizing when "Area" $\neq$ "Integral" due to sign.
    *   *Example:* Area enclosed by $y = x^2$, $y=-x$, $x=1$, $x=3$ (Q7).
*   **Band 7-9 (Advanced):** Conceptual manipulation of integrals without explicit function forms.
    *   *Logic:* Using properties of odd/even functions (Q15), combining integrals of different intervals to find unknown parts (Q5), or analyzing the error in the Trapezium Rule (Q24, Q28).

## 3. Arithmetic & Calculator Constraints
*   **Non-Calculator Friendly:** Surds ($\sqrt{2}, \sqrt{5}$) and fractions ($\frac{16\sqrt{2}}{7}$) are preferred over decimals.
*   **Answer Options:**
    *   Often expressed in terms of $\pi$ or $\sqrt{x}$.
    *   "Impossible" numbers are common intermediate steps (e.g., the answer to Q10 is $\frac{28 - 12\sqrt{5}}{3}$).
*   **Expansion Tricks:** Questions often hide polynomials inside binomial expansions.
    *   *Example:* Integrating $(3+2t)^7$ effectively requires recognizing the binomial coefficients to extract the $x^4$ term of the integral result (Q6).

## 4. Wording Conventions
*   **"Area enclosed between...":** Almost always implies $\int (Top - Bottom) \, dx$. Requires finding intersection points as limits.
*   **"Sufficient condition":** TMUA/ESAT logic questions often use this phrasing. It asks to identify a statement that guarantees the result (e.g., Q15).
*   **"Total area":** Explicitly demands the sum of positive areas, $\int |f(x)| \, dx$, distinct from the definite integral (Q18).
