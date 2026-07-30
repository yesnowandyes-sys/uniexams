# ESAT Calculator-Free Arithmetic & Symbols Research

> **Source:** ESAT Content Specification (April 2025), ENGAA 2023 past paper analysis,
> ESAT Guide documents (June 2025), ESAT preparation materials (esat-tmua.ac.uk),
> UEIE preparation analysis, TMUA conventions, and A-level/IGCSE calculator-free conventions.
>
> **Key finding:** The ESAT Content Specification explicitly states **"Calculators may NOT be used"**
> and that **g is approximated as 10 N kg⁻¹ on Earth** (specification P3.5b).

---

## 1. Mental Maths Skills Tested in ESAT

### 1.1 What the Specification Explicitly Requires

The ESAT Content Specification (M2: Number) requires candidates to:

- **M2.2:** Apply four operations to integers, decimals, simple fractions, and mixed numbers (positive and negative)
- **M2.6:** Use square, positive/negative square root, cube, and cube root
- **M2.8:** Standard form (a × 10ⁿ where 1 ≤ a < 10)
- **M2.11:** **Calculate exactly with fractions, surds, and multiples of π.** Simplify surd expressions (e.g. √12 = 2√3) and rationalise denominators
- **M2.13:** Round to appropriate decimal places / significant figures
- **M2.14:** **Use approximation to produce estimates of calculations, including expressions involving π or surds**
- **M5.18:** Know exact trig values: sin θ and cos θ for θ = 0°, 30°, 45°, 60°, 90°; tan θ for 0°, 30°, 45°, 60°

Mathematics 2 additionally requires (MM4.3): exact values of sin/cos/tan for 0°, 30°, 45°, 60°, 90°.

### 1.2 Evidence from Real Questions (ENGAA 2023 + ESAT specimen papers)

From the ENGAA 2023 paper analysis:

- **g = 10 N kg⁻¹** is explicitly stated in every physics question involving gravity (confirmed in multiple questions)
- Angles used: **30°** (slope angle, plank angle) — always standard angles
- Surdic answer options appear naturally: e.g. R = √(5)r, R = (√10/3)r
- Ratios used: 1:2, 3:1, 4:1 (simple integer ratios)
- Masses: 10,000 kg (round numbers), 1000 N (round numbers)
- Resistances: 10 Ω (round numbers)
- Voltages: 20 V (round numbers)
- Fractions in answer options: 1/3, 2/5, 9/20, 1/30, 19/60, 23/60
- Indices: 27^(...) / 9^(...) = ... type problems (exact power manipulation)
- Energy: 0.015 J (requiring decimal manipulation but not extreme precision)
- Springs: 200 N m⁻¹ and 600 N m⁻¹ (ratio-friendly numbers)

### 1.3 Key Mental Maths Skills

#### a) Surds
Surds are **explicitly tested**. Students must:
- Simplify √12, √18, √20, √24, √27, √28, √32, √45, √48, √50, √72, √75, √98, √108, etc.
- Rationalise denominators: 1/√3, 5/(√3+√5), 3/(2−√3)
- Leave answers in surd form (e.g. √5 r, 2√3)
- Estimate surd values when needed (e.g. √2 ≈ 1.41, √3 ≈ 1.73, √5 ≈ 2.24)

#### b) Standard Trig Values (Exact)
| Angle | sin θ | cos θ | tan θ |
|-------|-------|-------|-------|
| 0°    | 0     | 1     | 0     |
| 30°   | 1/2   | √3/2  | 1/√3  |
| 45°   | 1/√2  | 1/√2  | 1     |
| 60°   | √3/2  | 1/2   | √3    |
| 90°   | 1     | 0     | undefined |

These are **examinable** — non-standard angles (e.g. sin 23°) are NOT used unless estimation is acceptable.

#### c) Fractions
Students must manipulate fractions mentally:
- Addition/subtraction with different denominators (up to ~12)
- Multiplication: e.g. 3/7 × 14 = 6
- Cancellation and simplification
- Conversion between fractions, decimals, and percentages

#### d) Estimation
M2.14 explicitly tests estimation. Students should:
- Estimate π ≈ 3 or 3.14 depending on context
- Estimate surds: √2 ≈ 1.4, √3 ≈ 1.7, √5 ≈ 2.2, √7 ≈ 2.6
- Use ≈ symbol appropriately
- Know when exact vs approximate answers are needed

#### e) Indices and Standard Form
- Powers of 2, 3, 4, 5, 10 up to reasonable limits
- Negative and fractional indices
- Standard form conversion and arithmetic

#### f) Times Tables and Integer Arithmetic
- Full 12×12 times tables expected
- Multiplication of 2-digit by 1-digit mentally
- Simple 2-digit × 2-digit when numbers have nice structure (e.g. 12 × 15 = 180)
- Division by single digits and common 2-digit divisors

#### g) g Value Convention
**g = 10 N kg⁻¹** — this is explicitly stated in specification P3.5b and every physics question involving gravity. NOT 9.8 or 9.81.

### 1.4 What is NOT Reasonable Mentally

The following should be **flagged** by the checker as inappropriate for a calculator-free exam:

- **Multiplying two arbitrary 2-digit numbers** with no nice structure (e.g. 37 × 43)
- **Square roots of non-perfect, non-standard squares** (e.g. √17 to 3 decimal places)
- **Trigonometric values for non-standard angles** (e.g. sin 23°, cos 47°) unless the question explicitly says "estimate"
- **Logarithms requiring calculator evaluation** (e.g. log₁₀(7)). Note: log problems where the answer can be found by rewriting in powers are fine (e.g. log₂(8) = 3)
- **Three or more decimal place precision** in final numerical answers
- **Division by numbers > 12** that don't yield terminating decimals (unless fraction answer is acceptable)
- **Multiplying numbers > 20 × 20** unless there's nice structure (e.g. 25 × 24 = 600)
- **Physical constants requiring memorisation beyond g = 10** (specific heat capacities are always given in questions)

---

## 2. Calculator-Free Ruleset

### 2.1 ALLOWED Values and Operations

```python
# ALLOWED — these should NOT be flagged

# g value
ALLOWED_G = [10]  # g = 10 N/kg, always

# Standard angles (degrees)
ALLOWED_ANGLES_DEG = [0, 30, 45, 60, 90, 180, 270, 360]

# Standard angles (radians) — Maths 2 only
ALLOWED_ANGLES_RAD = [0, pi/6, pi/4, pi/3, pi/2, pi, 3*pi/2, 2*pi]

# Perfect squares up to reasonable limit
PERFECT_SQUARES = {1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225, 256, 289, 324, 361, 400}

# Perfect cubes
PERFECT_CUBES = {1, 8, 27, 64, 125, 216, 343, 512, 729, 1000}

# "Nice" surds that students should know or can derive
NICE_SURDS = {2, 3, 5, 6, 7, 8, 10, 12, 15, 20, 24, 30}  # √n values that appear in standard problems

# Multiplication thresholds
MAX_SIMPLE_MULTIPLY = (12, 20)  # a × b where a ≤ 12 and b ≤ 20 is OK
MAX_NICE_MULTIPLY = (25, 30)   # 25 × anything up to 30 is OK (25 × 4 = 100 structure)

# Powers students should know
KNOWN_POWERS = {
    2: [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024],
    3: [1, 3, 9, 27, 81, 243, 729],
    5: [1, 5, 25, 125, 625],
    10: [1, 10, 100, 1000, 10000, 100000],
}

# Logarithms — only where argument and base are powers of same integer
# e.g. log_2(8) = 3, log_3(81) = 4, log_10(1000) = 3
ALLOWED_LOG_BASES = [2, 3, 5, 10]  # with arguments that are exact powers

# Standard approximations students may use
APPROX_VALUES = {
    'pi': [3.14, 3.142, 22/7],  # π ≈ 3.14 acceptable
    'sqrt2': [1.414, 1.41],
    'sqrt3': [1.732, 1.73],
    'sqrt5': [2.236, 2.24],
    'e': [2.718, 2.72],  # rarely needed
}

# Decimal precision in answers
MAX_DECIMAL_PLACES = 3  # but flag if more than 2 significant figures needed
MAX_SIG_FIGS = 3

# Fraction denominators students should handle mentally
ALLOWED_FRACTION_DENOMINATORS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 20]
```

### 2.2 FLAG Conditions

```python
# FLAG — these need investigation

def should_flag(value, context):
    flags = []

    # g value check
    if hasattr(value, 'g_value') and value.g_value not in [10]:
        flags.append(f"g = {value.g_value} used; ESAT convention is g = 10 N/kg")

    # Non-standard angle
    if hasattr(value, 'angle_deg') and value.angle_deg not in ALLOWED_ANGLES_DEG:
        if not context.get('estimation_allowed', False):
            flags.append(f"Non-standard angle {value.angle_deg}° used without estimation context")

    # Large multiplication
    if hasattr(value, 'factors'):
        for a, b in value.factors:
            if a > 12 and b > 12 and not is_nice_product(a, b):
                flags.append(f"Multiplication {a} × {b} not readily mentally computable")

    # Non-perfect square root requiring decimal
    if hasattr(value, 'sqrt_n') and value.sqrt_n not in PERFECT_SQUARES:
        if value.sqrt_n not in NICE_SURDS and not context.get('exact_surd_ok', True):
            flags.append(f"√{value.sqrt_n} is not a standard surd value")

    # Non-standard log
    if hasattr(value, 'log_expr'):
        base, arg = value.log_expr
        if not is_exact_power(base, arg):
            flags.append(f"log_{base}({arg}) requires calculator")

    # Too many decimal places
    if hasattr(value, 'decimal_places') and value.decimal_places > MAX_DECIMAL_PLACES:
        flags.append(f"{value.decimal_places} decimal places — too precise for mental arithmetic")

    # Non-terminating decimal result required to > 2 dp
    if hasattr(value, 'requires_precision_dp') and value.requires_precision_dp > 2:
        flags.append(f"Answer requires {value.requires_precision_dp} dp — too precise")

    return flags

def is_nice_product(a, b):
    """Check if a × b has nice mental structure."""
    # Multiples of 10
    if a % 10 == 0 or b % 10 == 0: return True
    # 25 × something
    if a == 25 or b == 25: return True
    # Doubles/halves
    if a == 2 * b or b == 2 * a: return True
    # Near-squares
    if abs(a - b) <= 1 and a <= 15: return True
    # 11 × something ≤ 19
    if (a == 11 and b <= 19) or (b == 11 and a <= 19): return True
    return False

def is_exact_power(base, arg):
    """Check if arg is an exact power of base."""
    if base <= 1 or arg <= 0: return False
    p = 1
    for _ in range(20):
        p *= base
        if p == arg: return True
        if p > arg * 100: break
    return False
```

### 2.3 Estimation Rules

When a question involves estimation, the following relaxed rules apply:
- Non-standard angles may appear (e.g. "estimate sin 35°" → use sin 30° ≈ 0.5 as approximation)
- Surds may be approximated: √2 ≈ 1.4, √3 ≈ 1.7
- π may be approximated as 3 or 3.14
- Answer choices may differ by an order of magnitude (only one reasonable estimate)
- The question should use words like "approximately", "estimate", "best estimate"

### 2.4 Physics-Specific Conventions

| Quantity | Value Used | Notes |
|----------|-----------|-------|
| g (gravitational field strength) | **10 N kg⁻¹** | Explicitly stated in spec P3.5b |
| Speed of light, c | Given in question if needed | Not memorised |
| Specific heat capacity | Given in question | Never memorised |
| Avogadro's number, N_A | Given in question if needed | Concept known, value given |
| Molar gas volume at rtp | 24 dm³ | Mentioned in spec C4.8 as example |

---

## 3. Symbols and Notation by Module

### 3.1 Mathematical Symbols (All Modules)

| Symbol | Meaning | Used In |
|--------|---------|---------|
| =, ≠, <, >, ≤, ≥ | Comparison | All modules |
| +, −, ×, ÷ | Basic operations | All |
| ± | Plus or minus | Maths 1&2, Physics |
| √ | Square root | Maths 1&2 |
| ³√ | Cube root | Maths 1 |
| aⁿ | Power/index | All |
| a⁻ⁿ | Negative index | All |
| a^(1/n) | Fractional index | Maths 2 |
| π | Pi | All |
| ≈ | Approximately equal | All |
| ∝ | Proportional to | Physics, Maths 2 |
| ∞ | Infinity | Maths 2 |
| ∫ | Integral | Maths 2 |
| ∑ | Summation | Maths 2 |
| Δ | Change in (delta) | Physics, Chemistry |
| θ, φ, α, β | Angles | Maths, Physics |
| |x| | Modulus/absolute value | Maths 2 |
| f(x) | Function notation | Maths 1&2 |
| f′(x), f″(x) | First/second derivative | Maths 2 |
| dy/dx | Derivative | Maths 2 |
| d²y/dx² | Second derivative | Maths 2 |
| ⁿCᵣ | Binomial coefficient | Maths 2 |
| n! | Factorial | Maths 2 |
| logₐ x | Logarithm base a | Maths 2 |
| log x | Log base 10 (implied) | Maths 2 |
| ln x | Natural logarithm | NOT in spec — do not use |
| ∞ | Infinity | Maths 2 |

### 3.2 Greek Letters Used

| Letter | Name | Typical Usage | Module |
|--------|------|---------------|--------|
| α | alpha | Angular acceleration, angles | Physics, Maths |
| β | beta | Beta particle/radiation, angles | Physics, Chemistry |
| γ | gamma | Gamma radiation, ratio in physics | Physics |
| θ | theta | Angles (general) | All Maths/Physics |
| λ | lambda | Wavelength | Physics |
| μ | mu | Friction coefficient (not in spec but may appear) | Physics |
| ρ | rho | Density | Physics |
| σ | sigma | Stress, surface tension | Physics |
| τ | tau | Torque, time constant | Physics |
| ω | omega | Angular velocity | Physics |
| Δ | Delta | Change in quantity | All |
| ε | epsilon | Permittivity (may be given) | Physics |
| θ | theta | Angle | All |

### 3.3 Vector Notation
- ESAT uses **bold type** for vectors in print (e.g. **F**, **v**, **p**)
- Arrows above symbols are NOT standard in ESAT
- Hat notation (î, ĵ, k̂) is NOT used — ESAT does not test vector components
- Vectors are treated as magnitudes with direction in 1D problems primarily
- Vector addition/subtraction and multiplication by scalar in spec (M5.19) uses column representation

### 3.4 Module-Specific Notation

#### Mathematics 1
- Standard algebraic notation: ab for a×b, 3y for 3×y, etc.
- Surds: √n, simplified forms like 2√3
- Standard form: a × 10ⁿ
- Fraction notation: both horizontal bar and / accepted
- Inequality notation: <, >, ≤, ≥
- Interval notation: NOT used (spec uses number line or graph)
- Set notation: NOT required ("Candidates are not expected to know formal set theory notation" — M7.5)

#### Mathematics 2
- Function notation: f(x), f′(x), f″(x)
- Calculus notation: dy/dx, ∫ f(x) dx with bounds
- Binomial: ⁿCᵣ or C(n,r), n!
- Modulus: |x|
- Radian measure: π/6, π/4, π/3, etc.

#### Physics
- Standard circuit symbols (cell, battery, resistor, ammeter, voltmeter, switch, diode)
- Force diagrams with labelled arrows
- Graph labels: quantity / unit format (e.g. "velocity / m s⁻¹")
- Nuclear equations: ²³⁸₉₂U → ²³⁴₉₀Th + ⁴₂He
- Nuclide notation: ᴬ_ZX

#### Chemistry
- State symbols: (s), (l), (g), (aq)
- Chemical formulae: standard molecular formulae
- Isotope notation: ¹²₆C
- Oxidation states: Roman numerals e.g. iron(III)
- Ar, Mr (relative atomic/molar mass)
- pH (no formal definition beyond H⁺ concentration)
- ΔH (enthalpy change)
- Ea (activation energy)
- Electron configuration: 2,8,8,1 format (comma-separated)

#### Biology
- Genetic notation: alleles as letters (Tt, TT, tt)
- Punnett square notation
- Pedigree/family tree notation
- DNA base notation: A, T, G, C
- Sex chromosomes: XX, XY

---

## 4. Units by Module

### 4.1 SI Base Units (All Modules)

| Quantity | Unit | Symbol |
|----------|------|--------|
| Mass | kilogram | kg |
| Length | metre | m |
| Time | second | s |
| Temperature | degree Celsius | °C |
| Electric current | ampere | A |
| Amount of substance | mole | mol |

### 4.2 SI Prefixes (Explicitly in Spec)

| Prefix | Symbol | Power |
|--------|--------|-------|
| nano- | n | 10⁻⁹ |
| micro- | μ | 10⁻⁶ |
| milli- | m | 10⁻³ |
| centi- | c | 10⁻² |
| deci- | d | 10⁻¹ |
| kilo- | k | 10³ |
| mega- | M | 10⁶ |
| giga- | G | 10⁹ |

Note: Students must use negative indices in units (e.g. m s⁻¹ not m/s).

### 4.3 Derived Units by Module

#### Mathematics 1 & 2
| Quantity | Unit | Notes |
|----------|------|-------|
| Speed/velocity | m s⁻¹ | |
| Acceleration | m s⁻² | |
| Density | kg m⁻³ | |
| Pressure | Pa or N m⁻² | |

#### Physics
| Quantity | Unit | Notes |
|----------|------|-------|
| Force | newton, N | |
| Weight | newton, N | NOT kg |
| Energy/work | joule, J | |
| Power | watt, W | |
| Charge | coulomb, C | |
| Voltage/potential difference | volt, V | |
| Resistance | ohm, Ω | |
| Current | ampere, A | |
| Specific heat capacity | J kg⁻¹ °C⁻¹ | Always given in question |
| Frequency | hertz, Hz | |
| Wavelength | metre, m (or nm, μm) | |
| Magnetic field strength | tesla, T | May appear with F=BIL |
| Specific latent heat | J kg⁻¹ | Given in question |
| Density | kg m⁻³ | |
| Pressure | pascal, Pa or N m⁻² | |

#### Chemistry
| Quantity | Unit | Notes |
|----------|------|-------|
| Relative atomic mass | none (dimensionless) | Ar |
| Relative molecular mass | none (dimensionless) | Mr |
| Molar mass | g mol⁻¹ | |
| Concentration | mol dm⁻³ or g dm⁻³ | |
| Molar gas volume | dm³ mol⁻¹ | 24 dm³ at rtp |
| Energy change | kJ mol⁻¹ | (or J) |
| Temperature | °C or K | K if thermodynamics |
| Time | s or min | |
| Volume | cm³ or dm³ | |

#### Biology
| Quantity | Unit | Notes |
|----------|------|-------|
| Rate (transpiration) | cm³ s⁻¹ or cm³ min⁻¹ | volume/time |
| Population (density) | organisms per m² | |
| Percentage | % | |

### 4.4 Non-SI Units That May Appear

| Unit | For | Notes |
|------|-----|-------|
| degree (°) | Angle | Maths 1 uses degrees; Maths 2 uses both degrees and radians |
| radian (rad) | Angle | Maths 2 only |
| litre / dm³ | Volume | Chemistry — dm³ standard |
| cm³ | Volume | Common in Chemistry/Biology |
| minute (min) | Time | Biology, some Chemistry |
| kWh | Energy | NOT in spec — do not use |
| eV | Energy | NOT in spec — do not use |
| mmHg | Pressure | NOT in spec |
| atmosphere (atm) | Pressure | NOT in spec |
| calorie | Energy | NOT in spec |
| Å (angstrom) | Length | NOT in spec |

### 4.5 Units NOT in ESAT (Common in A-level but Excluded)

- kWh, MWh (energy)
- eV, MeV (energy)
- light-year, parsec (distance)
- mmHg, atm, bar (pressure)
- mph, km/h (speed — use m s⁻¹)
- Tesla (T) is technically allowed via F=BIL but rarely appears with explicit units
- Weber (Wb), Henry (H) — NOT in spec
- Siemens (S) — NOT in spec

---

## 5. Recommendations for Generation System

### 5.1 System Prompt Guidelines

When generating ESAT questions, the LLM should be instructed:

```
NUMERICAL CONVENTIONS:
- g = 10 N kg⁻¹ (always, stated in question if physics involves gravity)
- Use only standard angles: 0°, 30°, 45°, 60°, 90° (and multiples)
- Use round numbers for given values: masses in multiples of 0.1/0.5/1/2/5/10/100/1000
- Resistances: multiples of 1, 2, 5, 10, 20, 50, 100 Ω
- Voltages: multiples of 1, 2, 3, 6, 9, 12, 20, 24 V
- Answer options should be expressible as: exact fractions, terminating decimals (≤3 dp),
  exact surds (e.g. 2√3), or expressions involving π
- Do NOT require evaluation of: sin(23°), log₁₀(7), √17 to 3 dp, 37×43
- All specific heat capacities, latent heats, and physical constants MUST be given in the question
- Estimation questions must use the word "estimate" or "approximately"

NOTATION:
- Use standard SI units with negative indices (m s⁻¹, not m/s)
- Bold for vectors is acceptable
- Degrees for Maths 1/Physics; radians acceptable in Maths 2
- State symbols (s), (l), (g), (aq) in chemistry equations
- Nuclide notation: ᴬ_ZX
- Electron configuration: comma-separated (2,8,8,1)
```

### 5.2 Python Checker Implementation Priority

**Tier 1 — Must-check (flag as error):**
1. g ≠ 10 in any physics calculation
2. Non-standard angle used without "estimate" context
3. Final answer requiring > 3 significant figures
4. Multiplication of two numbers both > 15 with no nice structure
5. Non-terminating decimal required to > 2 dp
6. logₐ(b) where b is not an exact power of a
7. Missing physical constants (c, SHC, etc. not given in question)

**Tier 2 — Should-check (flag as warning):**
1. Square roots of non-perfect, non-standard numbers
2. Fractions with denominators > 12 in non-exact contexts
3. Decimal precision in given values exceeding 3 significant figures
4. Non-SI units used (kWh, eV, atm, etc.)
5. Negative index notation not used in compound units (e.g. "m/s" instead of "m s⁻¹")

**Tier 3 — Nice-to-check (flag as info):**
1. Whether answer options include surd forms correctly simplified
2. Whether standard form is used correctly
3. Whether estimation questions clearly signal that estimation is expected
4. Whether all answer options are "distinguishable" (no two answers so close they're indistinguishable mentally)

### 5.3 Question Generation Number Guidelines

For the question generator, use these "safe" number pools:

```python
SAFE_NUMBERS = {
    'masses_kg': [0.1, 0.2, 0.5, 1, 2, 3, 4, 5, 10, 20, 50, 100, 1000, 10000],
    'velocities': [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30],
    'forces_N': [1, 2, 3, 4, 5, 8, 10, 12, 15, 20, 25, 50, 100, 500, 1000],
    'resistances': [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 50, 100, 200, 600],
    'voltages': [1, 2, 3, 4, 5, 6, 9, 10, 12, 20, 24],
    'distances_m': [0.1, 0.2, 0.5, 1, 2, 3, 5, 10, 20, 50, 100],
    'angles_deg': [0, 30, 45, 60, 90],
    'spring_constants': [10, 20, 50, 100, 200, 400, 600],
    'times_s': [1, 2, 3, 4, 5, 10, 20, 30, 60, 100],
    'densities': [200, 400, 500, 800, 1000, 1200, 1500, 2000, 2500, 3000, 8000, 19000],
    'temperatures': [0, 10, 20, 25, 37, 50, 100],
}
```

### 5.4 Summary Checklist for Generated Questions

Before a generated question is accepted, verify:

- [ ] g = 10 N kg⁻¹ (if gravity involved)
- [ ] All angles from {0°, 30°, 45°, 60°, 90°} (unless estimation question)
- [ ] All physical constants given in question stem
- [ ] Arithmetic in the solution path is mentally feasible
- [ ] Answer options use exact forms (fractions, surds, π) or terminating decimals
- [ ] No answer requires more than 3 significant figures
- [ ] No multiplication of two numbers > 15 without nice structure
- [ ] All logarithms reduce to exact integer answers
- [ ] Units use SI with negative indices
- [ ] Appropriate notation for the module (degrees for Maths 1, radians OK for Maths 2)

---

## Appendix A: Standard Trig Values (Exact)

| θ° | θ rad | sin θ | cos θ | tan θ |
|----|-------|-------|-------|-------|
| 0° | 0 | 0 | 1 | 0 |
| 30° | π/6 | 1/2 | √3/2 | 1/√3 = √3/3 |
| 45° | π/4 | 1/√2 = √2/2 | 1/√2 = √2/2 | 1 |
| 60° | π/3 | √3/2 | 1/2 | √3 |
| 90° | π/2 | 1 | 0 | undefined |

## Appendix B: Standard Surd Simplifications

| Original | Simplified |
|----------|-----------|
| √8 | 2√2 |
| √12 | 2√3 |
| √18 | 3√2 |
| √20 | 2√5 |
| √24 | 2√6 |
| √27 | 3√3 |
| √28 | 2√7 |
| √32 | 4√2 |
| √45 | 3√5 |
| √48 | 4√3 |
| √50 | 5√2 |
| √72 | 6√2 |
| √75 | 5√3 |
| √98 | 7√2 |
| √108 | 6√3 |

## Appendix C: Powers to Know

| n | 2ⁿ | 3ⁿ | 5ⁿ | 10ⁿ |
|---|-----|-----|-----|------|
| 1 | 2 | 3 | 5 | 10 |
| 2 | 4 | 9 | 25 | 100 |
| 3 | 8 | 27 | 125 | 1,000 |
| 4 | 16 | 81 | 625 | 10,000 |
| 5 | 32 | 243 | 3,125 | 100,000 |
| 6 | 64 | 729 | — | 1,000,000 |
| 7 | 128 | — | — | — |
| 8 | 256 | — | — | — |
| 9 | 512 | — | — | — |
| 10 | 1,024 | — | — | — |
