# Style Guide — PHYS.P2 (Magnetism)

- Module: Physics (P)
- Corpus questions classified under this topic: 10
- corpus_backed: True

---

### Arithmetic and Complexity
*   **Calculator-Free Arithmetic**: Calculations are designed to be completed without a calculator. They rely on "friendly" numbers (integers, simple decimals like 0.5, 0.6) and prefixes (milli, centi) that align with powers of 10.
    *   *Example (Q1)*: $0.60 \times 0.050 \times 50 \times 0.04$. The math simplifies to $6 \times 5 \times 2 \times 10^{-4}$, which is manageable mentally.
*   **Unit Consistency**: A major testing vector is unit management.
    *   Inputs are often mixed (cm vs m, minutes vs seconds).
    *   Output requirements often switch units (e.g., calculate in meters, report in cm).
    *   *Pattern*: Inputs frequently involve multiples of 12, 15, 60 (time conversions) or 100 (cm to m).

### Diagram and Visual Dependency
*   **Geometry of Fields**: Questions almost always reference a diagram (even if not provided in the text prompt, the text describes a specific spatial arrangement).
    *   *Keywords*: "Perpendicular into the page", "Horizontal from left to right", "Seen from above".
*   **Visualizing Vectors**: Success requires visualizing 3D vector relationships on a 2D plane (Cross Product Rule).
    *   *Pattern*: "Horizontal wire... North-South direction... Field West-East". This forces the student to construct a 3D coordinate system in their mind.

### Conceptual Scenarios
*   **Dynamic vs Static**:
    *   *Static (Motor Effect)*: Calculating Force/Torque on a current-carrying wire in a B-field (Q1, Q2, Q6).
    *   *Dynamic (Generator Effect)*: Induced EMF/Current due to changing flux or motion (Q4, Q8, Q9).
    *   *Steady State*: Transformers or DC currents (Q3, Q5).
*   **Geometric Constraints**:
    *   Problems often feature "effective length" traps (Q2, Q1).
    *   *Pattern*: "Part of the coil is between the poles..." (Q1) or "Rod of length 20cm... rails 12cm apart" (Q2). This tests if the student uses the *magnetic* geometry rather than the *object* geometry.

### Wording Conventions
*   **Precision in Direction**: Directional language is exact. "North to South", "Into the page", "Clockwise".
*   **Magnitude Prompts**: Questions often ask for "moment" or "acceleration" (combined quantity) rather than just "force", requiring an extra step of synthesis (e.g., $a = F/m$, $\tau = F \times d$).
