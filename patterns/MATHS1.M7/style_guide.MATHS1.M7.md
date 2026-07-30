# Style Guide — MATHS1.M7 (Probability)

- Module: Mathematics 1 (M1)
- Corpus questions classified under this topic: 28
- corpus_backed: True

---

## Question Structure and Framing

**Contextualization:**
Questions in this domain (M7) are rarely abstract. They are grounded in concrete, semi-realistic scenarios involving "students choosing activities," "sweets in a bowl," or "coloured balls/counters in bags." The context serves to mask standard probability mechanisms (combinatorics, conditional probability, geometric series).

*   **Constraint Logic:** Scenarios often involve specific constraints or procedural rules.
    *   *Example (Q3, Q14):* "If the sweet is green, it is not replaced and the child takes another sweet." This forces a conditional (Markov-like) calculation or geometric series sum.
    *   *Example (Q7):* Nested conditions: "If the bus is on time... then the prob of train is..." This enforces the use of Tree Diagrams or Bayes' Theorem.

**Wording Conventions:**
*   **"Identical in all respects except...":** A standard phrase used to indicate that physical properties (texture, size) do not affect selection, only the variable of interest (colour) does.
*   **"Chosen at random" / "Equally likely":** Establishes the uniform distribution baseline.
*   **"Given that...":** The standard marker for conditional probability (P(A|B)).
*   **"Without replacement" vs implicit non-replacement:** Explicit instructions are sometimes given, but often the rule is described narratively ("eaten," "kept," or "not placed back").

## Difficulty Calibration

*   **Band 1-3 (Foundation):**
    *   Single-stage probability (e.g., Q9: simple independent product rule).
    *   Two-way table extraction (Q1: populating a table and reading a ratio).
    *   Expected value calculations.
*   **Band 4-6 (Intermediate):**
    *   Combinatorics with constraints (Q5: determining population composition N based on probability output, then recalculating).
    *   "At least one" calculations requiring complements (Q17).
    *   Non-uniform dice or spinners (Q20: distinct face labels).
*   **Band 7-9 (Advanced):**
    *   Induction / Iteration (Q3/Q14: "Continues until..." requiring summation of 1/2 + 1/3... style series).
    *   Reverse Probability (Q21: given final P, determine intermediate variable $x$).
    *   Complex Systems (Q24: Logic/Probability hybrids, Q8: solving for unknowns in a system).

## Calculator-Free Arithmetic Patterns

*   **Fractional Logic:** The calculator ban necessitates questions designed for fractional arithmetic.
    *   *Cancellation:* Inputs are designed to cancel heavily (e.g., Q2: $\frac{x}{x+4} \times \frac{x-1}{x+3} = \frac{1}{3}$).
    *   *Quadratic Forms:* In variable-finding questions (Q5, Q2), the algebra reduces to integer solutions ($x(x-1) = 56 \rightarrow x=8$) to avoid decimal approximations.
*   **Sample Spaces:** Dice/Spinner sums (Q4, Q20) rely on small integer counts (e.g., 36 outcomes) where probabilities are simple fractions like 1/8, 5/36.
*   **Visualizing Fractions:** Correct options often share denominators with incorrect options (e.g., Q1 options: 9/37 vs 16/37). This forces the student to calculate the *numerator* exactly, as estimation is impossible.

## Topic Distribution Correlation
*   **M7.1/M7.2 (Frequency Trees/Tables):** Q1, Q10, Q11, Q13, Q15.
*   **M7.5 (Independence/Tree Diagrams):** Q7, Q8, Q9, Q21, Q26.
*   **M7.6 (Conditional Probability):** Q1, Q7, Q11.
*   **M7.7 (Experimental/Expected):** Implicit in Q11 (population stats) and Q13 (Venn/frequency logic).
