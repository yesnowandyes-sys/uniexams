# Style Guide — CHEM.C3 (Chemical reactions, formulae and equations)

- Module: Chemistry (C)
- Corpus questions classified under this topic: 19
- corpus_backed: True

---

## Question Structure Patterns

*   **Stoichiometric Balancing (Algebraic):** A common format involves presenting a skeletal equation with algebraic coefficients (e.g., $v \text{Q} + w \text{P}_4 + x \text{H}_2\text{O}$). The question asks for the value of a specific coefficient (e.g., Q2, Q8, Q12) or the sum of all coefficients (Q9).
    *   *Complexity:* Questions often involve redox reactions where oxidation states change, requiring tracking of electron loss/gain alongside standard atom balancing (Q7, Q9, Q19).
*   **Formula Derivation:** Questions test the ability to construct formulae from ion charges or empirical data.
    *   *Types:* "Mixed oxidation state" problems (Q1), "Ionic precipitation" selecting the correct balanced ionic equation from a list (Q6), and "Common compound" verification (Q11).
*   **Quantitative Gas Chemistry:** These questions link mass/moles to gas volume, often at non-standard conditions or with specific reactant constraints.
    *   *Constraint-based:* "Limited supply of oxygen" problems requiring algebraic representation of product ratios (Q17).
    *   *State-aware:* Questions explicitly mentioning temperature to force the student to recognize the physical state of water (gas vs liquid) for volume calculations (Q13).
*   **Deductive Identity:** Students are given qualitative information (e.g., colour changes, lack of specific elements) and quantitative ratios (moles of reactant A vs moles of product B) to identify a mystery product (Q4, Q14).

## Difficulty Calibration

*   **Easy (Band 1-3):** Direct formula writing from known ions (Q11), simple molar mass/volume calculations with 1:1 stoichiometry (Q5 logic), and identifying redox oxidation states in simple single-step equations.
*   **Medium (Band 4-6):** Balancing equations with 3-4 variables, calculating ratios in mixed oxidation states (Q1), empirical formula derivation from experimental data (Q3).
*   **Hard (Band 7-9):** Complex algebraic balancing (Q9, Q19), simultaneous stoichiometry and gas volume calculations with state-phase awareness (Q13), and limiting reagent problems with algebraic product distributions (Q17).

## Wording Conventions

*   **Precision on Elements:** Phrases like "does not contain copper or hydrogen" (Q4) are strict constraints used to eliminate candidate products based on atomic composition.
*   **Molar Quantifiers:** Explicit use of "1 mole of gas occupies 24.0 dm³" (Q5) serves as a conversion factor anchor. In gas questions, volumes are typically given in cm³ or dm³.
*   **Conditionals:** Statements like "Assuming 1 mole of gas..." or "at atmospheric pressure and a temperature of 150°C" are critical triggers that modify the standard calculation approach (e.g., $V \propto n$ still holds, but the nature of the products changes).

## Calculator-Free Arithmetic Patterns

*   **Arithmetics:** The numbers are chosen to cancel out cleanly.
    *   Masses often divide neatly into molar masses (e.g., $7.2 / 48 = 0.15$, or $7.2/24 = 0.3$ in TiO question Q3 logic, or $0.35 / 7 = 0.05$ in Q5).
    *   Coefficients in balanced equations are typically integers between 1 and 10, or simple fractions like 1.5, 2.5 which are then multiplied to clear denominators.
*   **Algebraic over Numerical:** In hard questions, the "arithmetic" is substituting values into an algebraic expression to find the sum $x+y+z$. The distractors are often the result of adding *unmultiplied* fractions (e.g., adding $0.5 + 1.5$ instead of $1 + 3$).
