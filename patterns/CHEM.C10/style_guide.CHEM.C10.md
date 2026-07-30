# Style Guide — CHEM.C10 (Rates of reaction)

- Module: Chemistry (C)
- Corpus questions classified under this topic: 18
- corpus_backed: True

---

# Style Guide for CHEM.C10 (Rates of Reaction)

## Question Structure Patterns

*   **Comparative Experiments (The "Which Graph" Problem):**
    *   **Format:** A base experiment (Line P or Graph 1) is described. A second experiment is described with altered conditions (concentration, volume, temperature, surface area). The student must select the correct modified graph from a set (usually A-F).
    *   **Key Elements:** Always specifies "excess" of one reactant to define the limiting reagent clearly.
    *   **Frequency:** Very High (Q1, Q5, Q9, Q12, Q13, Q15).
    *   **Variations:**
        *   *Concentration/Volume Trade-off:* Doubling concentration but halving volume (Q5, Q13). Tests if the student understands initial rate (gradient) vs. total yield (plateau).
        *   *Surface Area vs. Mass:* Comparing chips vs. powder, or small mass vs. large mass (Q12, Q15). Tests understanding that initial rate depends on surface area, but final yield depends on total moles.

*   **Le Chatelier vs. Kinetics (The "Two Conditions" Problem):**
    *   **Format:** A reversible reaction is described. A condition (Temp or Pressure) is changed. The student must determine the effect on **both** the Rate of Reaction and the Equilibrium Yield.
    *   **Complexity:** Requires analyzing the stoichiometry (moles of gas) and enthalpy ($\Delta H$ sign).
    *   **Frequency:** High (Q2, Q4, Q8).

*   **Data Calculation (The "Rate" Problem):**
    *   **Format:** A table or graph is provided with raw data (Volume of gas vs. Time, or Mass loss vs. Time). The student must calculate the average rate.
    *   **Skills:** Unit conversion ($\text{cm}^3$ to moles, moles to grams), handling time, gradient calculation.
    *   **Frequency:** Medium (Q11, Q14, Q15).

## Difficulty Calibration

*   **Band 4-6 (Medium):**
    *   Single variable analysis (e.g., "What happens to rate if temperature increases?").
    *   Identifying parts of an energy level diagram (Q3).
    *   Simple definition checks (collision theory).
*   **Band 7-9 (Hard):**
    *   **Multi-variable comparative graphs:** Distinguishing between *steeper gradient* (rate) and *higher plateau* (yield) simultaneously (Q5, Q12).
    *   **Reconciling conflicting conditions:** e.g., "Temp increases rate, but yield decreases" vs "Pressure increases rate, yield unchanged" (Q2, Q8). This requires high logical load.
    *   **Quantitative prediction:** Interpreting stoichiometry to determine yield in a graph problem before the graph is even analyzed.

## Wording Conventions

*   **"Equimolar samples":** Used to imply initial concentrations are equal (Q1).
*   **"Excess":** Crucial keyword. It signals that the reactant in solution is the limiting reagent, and the gas volume depends only on the solution, not the solid.
*   **"In the shortest time":** Implies a comparison of rates, but requires checking that the final yield is actually possible (e.g., don't pick the 'fast' reaction if it runs out of acid).
*   **"Assume that one mole of gas occupies a volume of 24 dm3":** Standard assumption for calculator-free math.
*   **"The reaction goes to completion":** Signals a single-direction reaction kinetics context, distinct from equilibrium.

## Calculator-Free Arithmetic Patterns

*   **Molar Volume simplification:** $24 \text{ dm}^3/\text{mol}$ is standard.
    *   *Implied calculation:* $\text{Mass (g)} / 24 = \text{Volume (cm}^3)$ is false.
    *   *Correct flow:* Mass $\to$ Moles $\to$ Volume (x24).
    *   *Shortcut:* Often, $Ar$ values are multiples of 24 (e.g., Mg=24, C=12). $1 \text{ g Mg} \to 1/24 \text{ mol} \to 1 \text{ dm}^3 \text{ gas}$.
*   **Rate simplifications:** Time is often 60, 100, or 120 seconds. Volumes are often integers (e.g., 100, 50).
    *   *Q11:* $48 \text{ cm}^3 / 2 \text{ s} \to 24 \text{ cm}^3/\text{s}$.
    *   Then convert $24 \text{ cm}^3$ to moles: $24/24000 = 0.001 \text{ mol}$.
    *   Then to mass: $0.001 \times 24 = 0.024 \text{ g}$.
    *   Rate: $0.024 / 2 = 0.012 \text{ g/s}$.
*   **Concentration vs Volume:**
    *   Common setup: $50 \text{ cm}^3$ of $2.0 \text{ M}$ vs $100 \text{ cm}^3$ of $1.0 \text{ M}$.
    *   Total moles are identical ($1.0 \text{ mmol/cm}^3 \times 50 = 50$ vs $0.5 \text{ mmol/cm}^3 \times 100 = 50$).
    *   *Distractor:* Students double-count. "Double concentration means double gas!" (False).
