# Style Guide — CHEM.C1 (Atomic structure)

- Module: Chemistry (C)
- Corpus questions classified under this topic: 22
- corpus_backed: True

---

# ESAT Chemistry: Atomic Structure Style Guide

## 1. Calculator-Free Arithmetic Patterns
Questions in this domain rely on integer arithmetic and clean fraction/percentage math suitable for mental calculation.
*   **Percentages:** Abundance values typically sum to 100% using 'easy' splits (e.g., 50/50, 60/40, 80/20, 90/10).
    *   *Pattern:* `(0.6 * A) + (0.4 * B)` where A and B are simple integers.
*   **Atomic Mass Weighted Averages:**
    *   *Easy Splits:* Isotopes often differ by 1 or 2 mass units.
    *   *Ratios:* Often expressed as fractions like 2:1, 3:1, or 9:16 (derived from squaring simple integers) to avoid complex decimals.
    *   *Example:* Q18 uses $0.8 \times 14 + 0.2 \times 15 = 14.2$.
*   **Isotope Math:** Mass numbers are almost always integers. Relative atomic masses ($A_r$) are rarely integers, usually to 1 decimal place (e.g., 10.8, 24.3).

## 2. Notation and Formatting Conventions
*   **Nuclide Notation:** Standard `^{Mass}_{Number}Element_{Charge}` format is used, often without LaTeX rendering braces in plain text (e.g., `_{20}^{40}Ca^{2+}`).
*   **Electron Configuration:**
    *   Comma-separated format is standard (e.g., `2,8,8`).
    *   Occasionally 'dot-cross' diagrams are referenced, but answer choices always use the comma format for clarity.
*   **Variable Nomenclature:**
    *   $x$ or $Z$ usually denotes the atomic number (proton count).
    *   $A$ or $M$ denotes mass number.
    *   Neutron count is often derived as $A - Z$.
    *   Isotopes are often labelled generically (Isotope 1, Isotope 2) or by specific element notation.

## 3. Question Structure Patterns
*   **The "Isotope-Hopping" MCQ:**
    *   *Structure:* Defines a specific atom/ion (e.g., $^{40}Ca^{2+}$). Asks the student to identify a different species with identical properties (same number of neutrons, or same electrons).
    *   *Complexity:* Requires calculating protons, neutrons, and electrons for the source, then scanning options for a match that likely has a different atomic number.
*   **The "Algebraic Ion" Problem:**
    *   *Structure:* Defines mass number and charge in terms of atomic number $x$ (e.g., $A = 2x + 2$). Asks for expressions for $p, n, e$.
    *   *Complexity:* Tests algebraic manipulation of sub-atomic definitions.
*   **The "Abundance Calculation":**
    *   *Structure:* Provides two isotopes and their relative atomic mass. Requires reversing the weighted average formula to find the percentage abundance.
    *   *Complexity:* Often requires recognizing that the abundance is the difference from 100% or setting up a simple linear equation.

## 4. Difficulty Calibration
*   **Band 1-3:** Direct calculation of $p, n, e$ for a single given species. Basic isotope definition. Electron configuration of neutral atoms (H to Ca).
*   **Band 4-6:** Ions and charged species. Matching $p, n, e$ across different elements (isotopes/isobars). Simple weighted average calculations. Visual interpretations of spectra (identifying Group/Period).
*   **Band 7-9:** Algebraic sub-particle calculations. Molecular ion spectra patterns (e.g., GaCl3). Reverse abundance problems. Multi-step logical deductions involving ratios of isotopes.
