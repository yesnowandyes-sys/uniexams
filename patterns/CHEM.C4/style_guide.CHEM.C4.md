# Style Guide — CHEM.C4 (Quantitative chemistry)

- Module: Chemistry (C)
- Corpus questions classified under this topic: 61
- corpus_backed: True

---

### **Question Structure & Complexity**

*   **Multi-Step Reasoning:** Most questions are not single-step formula applications. They typically involve 3 stages of calculation:
    1.  **Conversion:** (Mass $\to$ Moles) or (Volume $\to$ Moles).
    2.  **Stoichiometry:** Applying mole ratios (often 1:1, but frequently 1:2, 2:3, etc.).
    3.  **Re-conversion/Result:** (Moles $\to$ Mass/Volume/Concentration).
    *   *Example:* Q4 (Stage 2 C $\to$ CO, Stage 3 CO $\to$ CO2).
*   **Scenario Embedding:** Quantitative skills are tested within chemical contexts.
    *   **Purity/Impurity:** Q5, Q9, Q16, Q23, Q44.
    *   **Combustion:** Q7, Q25, Q28, Q30.
    *   **Titration/Back-Titration:** Q5, Q13, Q31, Q44.
    *   **Gas Laws:** Q1, Q17, Q33.
    *   **Hydration/Water of Crystallisation:** Q15, Q49.
*   **Data Presentation:**
    *   Questions are text-heavy but provide clear **Ar** values in a dedicated line.
    *   **Equations:** Provided for all non-trivial reactions (e.g., Q4, Q5, Q6, Q13).
    *   **Constraints:** Constant T and P for gas questions are explicitly stated ("measured at the same temperature and pressure").

### **Difficulty Calibration**

*   **Level 1 (Direct):** Simple mole/mass conversion, simple empirical formula where ratios are obvious integers.
    *   *Artefacts:* Q2, Q19.
*   **Level 2 (Process):** Identifying limiting reagents, simple back-titrations, gas volume calculations requiring $n = V/24$.
    *   *Artefacts:* Q4, Q9, Q17.
*   **Level 3 (Complex):** Multi-step logic (e.g., neutralisation of excess acid in Q16), dilution series (Q26), reacting a gas mixture (Q28), determining Mr from an experiment (Q6).
    *   *Artefacts:* Q16, Q26, Q28, Q33.

### **Wording Conventions**

*   **"Excess":** Used explicitly to define the limiting reagent (e.g., Q4, Q7, Q17).
*   **"Impure":** Signals a purity calculation is required ($mass_{pure} = mass_{total} \times purity\%$).
*   **"Minimum":** Often used in titration/purity questions (e.g., Q5) or acid-base volume (Q27) to imply exact stoichiometric equivalence.
*   **"Measured at room temperature and pressure":** The trigger to use 24 $dm^3$ (or 24,000 $cm^3$) as the molar volume.
*   **Formula Presentation:** Formulae are written with standard subscripts (e.g., $H_2SO_4$). Ionic charges are often omitted unless relevant to the product (e.g., "ions in solution").

### **Calculator-Free Arithmetic Patterns**

*   **Integer Arithmetic:** The numbers are chosen to cancel out or yield integers early in the calculation.
    *   *Example:* $24 \text{ dm}^3$ is chosen because $Mr$ values often divide into it or it relates to scaling factors.
    *   *Example:* Q6 (Alkali XOH): $2.8 / (2 \times 0.0125 \times 2.0) = 2.8 / 0.05 = 56$. $56 - (16+1) = 39$. No complex decimals.
*   **Fractional Moles:** 0.5 or 0.25 moles appear frequently to allow for halving or doubling mental math.
    *   *Example:* Q12 uses 36g Steam ($2$ moles) to produce $2$ moles $H_2$ and $1$ mole $O_2$.
*   **Scaling:** Questions often ask for "Mass of..." where the mole ratio is $1:2$ or $2:1$. Students must be fluent in doubling/halving.
    *   *Example:* Q31 involves $0.005$ moles difference ($50 \times 0.1$ vs $5 \times 0.2 \times 0.5$).
*   **Avoid Long Division:** Arithmetic rarely requires dividing by primes like 7 or 13 unless the numbers are very small.
*   **Common Factors:** Molar masses provided are often multiples of 2, 3, 4, 5, 10 (e.g., $C=12, O=16, S=32, Fe=56$).
