# Style Guide — CHEM.C11 (Energetics)

- Module: Chemistry (C)
- Corpus questions classified under this topic: 20
- corpus_backed: True

---

# ESAT Chemistry (C11) Style Guide: Energetics

## Question Structure Patterns
Questions in this domain typically fall into three structural archetypes:
1.  **Hess Cycle / Born-Haber:** A textual description of thermodynamic steps (atomization, ionization, electron affinity, formation) or a reaction list. The student must sum values, often applying algebraic logic to find an unknown variable (e.g., Q20, Q14, Q16).
2.  **Bond Energy Algebra:** A reaction equation is provided with bond energies represented by variables ($x, y, z$). The student must derive an inequality or equation based on the formula $\Delta H = \Sigma E_{bonds broken} - \Sigma E_{bonds formed}$ (e.g., Q1).
3.  **Calorimetry Data Interpretation:**
    *   **Graphical:** A graph of temperature vs volume (titration) or temperature vs time. The student must read $\Delta T$ or identify the equivalence point (e.g., Q8, Q9, Q18).
    *   **Numeric:** "Recipe style" text describing masses, concentrations, and temperature changes. Requires calculating $q = mc\Delta T$ and dividing by moles (e.g., Q12, Q15).

## Difficulty Calibration
*   **Band 4-6:** Basic bond energy calculation using provided integer values. Direct application of $q=mc\Delta T$ where moles are clearly given.
*   **Band 7-9:** Algebraic manipulation of bond energies (inequalities). Born-Haber cycles requiring constructing a sum from 5+ steps. Calorimetry involving non-1:1 stoichiometry, unit conversions ($cm^3$ to $g$), or efficiency factors ($20\%$).

## Wording Conventions
*   **Heat released vs Enthalpy Change:** Distinguishing between $\Delta H$ (negative for exothermic) and "energy released" (positive magnitude). Questions often mix these (e.g., Q10 "2000 kJ released" vs Q11 "calculated energy change").
*   **"Mean Bond Energy":** Specific phrasing used to imply averaging over a specific environment, though in exams, treated as a standard lookup value.
*   **Assumptions:** Explicitly stated at the end of prompts: "density... is 1 $g cm^{-3}$", "no heat lost", "specific heat capacity... is 4 $J g^{-1} ^\circ C^{-1}$".

## Arithmetic Patterns (Calculator-Free)
*   **Integer Arithmetic:** All bond energies and $\Delta H$ values are integers (multiples of 1 or 5 kJ).
*   **Rounding:** Answers are usually distinct integers (e.g., -606, -990). In cases with decimals (e.g., Q8), the logic often leads to a clean integer after scaling, or the options are spaced sufficiently apart.
*   **Multiples:** Stoichiometry relies on small integer factors (2, 3, 4) and doubling/halving.
*   **Unit Prefixes:** Heavy reliance on converting $J$ to $kJ$ (factor of 1000) or $cm^3$ to $dm^3$ (factor of 1000).
    *   *Example:* $30 \times 20 = 600$ (simple), then $/ 1000$ for units.
