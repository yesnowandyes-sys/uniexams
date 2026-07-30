# Style Guide — PHYS.P7 (Radioactivity)

- Module: Physics (P)
- Corpus questions classified under this topic: 37
- corpus_backed: True

---

### Question Structure Patterns

**1. Algebraic Proofs of Conservation (Fission/Fusion)**
*   **Format:** A nuclear equation is presented with variables (e.g., `w, x, y, z`) representing mass numbers or atomic numbers. The prompt asks "Which equation is correct?" rather than solving for a specific value directly.
*   **Example Reference:** Q2, Q22.
*   **Requirement:** Test taker must construct two conservation equations (Mass: Top numbers; Charge: Bottom numbers) and identify the algebraic relationship between the variables (e.g., `z = 240 - (w + y)`).

**2. Multi-Step Ratio Logic (The "Rock Dating" Problem)**
*   **Format:** A sample contains Parent ($X$) and Daughter ($Y$). At $t=0$, quantities are equal or in a specific ratio. Question asks for the ratio $Y/X$ at a specific future time $t$ (usually a multiple of the half-life).
*   **Key Complexity:** The daughter product is often also present initially. The final amount is $Initial_{daughter} + Decayed_{parent}$.
*   **Example Reference:** Q11, Q33.
*   **Wording:** "When a rock formed it contained equal numbers of atoms of all four nuclides..."

**3. The "Net vs. Step" Paradox**
*   **Format:** A nuclide decays via specific particles (e.g., $1\alpha, 3\beta$). Question asks which nuclide *cannot* be formed.
*   **Trap:** The net change is fixed ($\Delta A, \Delta Z$), but the path matters. A state with net change properties might be impossible if the order of emissions prohibits it (e.g., atomic number drops too low before rising).
*   **Example Reference:** Q3, Q23.

### Difficulty Calibration & Calculator-Free Arithmetic

*   **Integer Constraint:** All half-life questions involve simple integer relationships (1 half-life, 2 half-lives, 4 half-lives).
    *   *Pattern:* "Time = 4T" (where T is half-life). The remaining fraction is always $1/2^4 = 1/16$.
    *   *Pattern:* Initial counts are usually powers of 2 or small integers (e.g., 1000 atoms).
*   **Answer Options:** Options for fractional amounts usually sum to 1 (e.g., 3/16 vs 13/16).
*   **Calculation Patterns:**
    *   **Simultaneous Decay:** Requires solving $2 \cdot (1/2)^{t/2} = 1 \cdot (1/2)^{t/3}$. Logs are not required; answer choices are integers (e.g., 6 days), allowing for trial-and-error or integer factor analysis.
    *   **Decay Series:** $Mass_{start} - Mass_{end} = 4n_\alpha$. Calculation is purely integer arithmetic.

### Wording Conventions

*   **"Succession of decays"**: Indicates multiple steps.
*   **"At any stage"**: Critical trigger for the Net vs. Step paradox questions.
*   **"Nuclide" vs "Isotope"**: Used precisely. Nuclide refers to specific nuclear species ($N, Z$); Isotope refers to members of an element family (same $Z$).
*   **"Count rate" vs "Activity"**: Often used interchangeably, but always implies the measured quantity, which may include background.
