# Style Guide — PHYS.P1 (Electricity)

- Module: Physics (P)
- Corpus questions classified under this topic: 78
- corpus_backed: True

---

## ESAT Topic PHYS.P1 (Electricity) Style Guide

### 1. Question Structure and Narrative
*   **Component Recognition:** Questions often begin with a description of a circuit containing standard components (resistors, lamps, diodes, thermistors, LDRs, transformers). Students are expected to interpret the behavior (e.g., "a lamp becomes short-circuited" implies resistance becomes 0).
*   **Multi-step reasoning:** Most questions require 2-3 distinct steps:
    1.  **Ohm's Law / Kirchhoff's Laws:** Finding total resistance or current.
    2.  **Power / Energy Formulas:** Applying P=IV, P=I²R, or E=VIt.
    3.  **Ratio / Scaling:** Applying the result to a new condition (e.g., "switch closed," "lamp removed").
*   **Variable Conditions:** Common prompts involve "variable resistors adjusted to..." or components changing state (heating up, shorting out), testing dynamic understanding rather than static calculation.

### 2. Difficulty Calibration
*   **Easy (Band 1-2):** Direct application of $P=VI$ or $E=Pt$ with unit conversions (e.g., minutes to seconds, kW to W). Simple series circuits.
*   **Medium (Band 3-4):** Combined series and parallel logic. Power distribution in identical resistor networks. Transformer turns ratios with power/efficiency. Geometry of resistance (length/area).
*   **Hard (Band 5-6):** Non-ohmic components (Filament Lamps/Thermistors) where R changes. Circuits with switches altering topology significantly (Series to Parallel changes). Resistance of conductors with volume conservation. "Short-circuit" logic in series strings.

### 3. Calculator-Free Arithmetic Patterns
*   **Power of 10 Coefficients:** Numbers are chosen to allow integer math despite scientific notation (e.g., $I = 4.0 \text{ A}$, $R = 1.6 \times 10^{-7} \Omega \text{m}$, $A = 4.0 \times 10^{-7} \text{m}^2 \rightarrow V = 0.80 \text{ V}$).
*   **Factorable Fractions:** Turn ratios (e.g., 100:25 = 4:1). Resistance values in parallel (e.g., $R_{eq}$ of two $R$ is $R/2$).
*   **Time Management:** Durations are often 60s, 2 mins, 30 mins, allowing easy conversion to seconds (x60) or combined with Power (kW) to give clean MegaJoule answers.
*   **Symbolic Logic:** For resistors R1, R2, options are often left as fractions (e.g., $\frac{V^2 R_1}{(R_1 + R_2)^2}$), requiring algebraic manipulation rather than numerical plug-in.

### 4. Wording Conventions
*   **Precision:** "Negligible resistance," "Ideal transformer," "Constant voltage."
*   **Action Verbs:** "What is the new reading," "How much charge passes," "What is the maximum power."
*   **Units:** Heavy use of SI prefixes ($k\Omega$, $mA$, $kV$, $kW$). Students must track these carefully.

### 5. Diagram Dependency
*   Circuit diagrams are almost always provided but not reproduced in the text corpus. Analysis must infer the topology from descriptions like "three resistors connected in series with a battery" or "diagram shows a circuit containing...".
*   Questions involving **Voltmeters** and **Ammeters** rely on the student knowing that Voltmeters are infinite resistance (open) and Ammeters are zero resistance (short) for the purpose of circuit calculations.
