# ARM64 Dependency Verification Report

**Task:** [ESAT/issues/ESA-20](/ESAT/issues/ESA-20)
**Agent:** Coding Agent
**Date:** 2026-07-11
**Host:** Oracle Cloud Ampere A1, `aarch64`, Ubuntu 24.04.4 LTS, Python 3.12.3, 4 vCPU / 23 GiB RAM

## TL;DR

All three ARM64-sensitive dependencies work on this host. **No fallback plan needs to be activated**, but documented below anyway per the task acceptance criteria. Two operational gotchas worth knowing up-front:

1. **`pdflatex` is not pre-installed on the base image.** Install it as part of the bootstrap script (commands below).
2. **`chemfig` + TikZ: do not name a user file `chemfig.tex` in the working directory** — `chemfig.sty` does `\input chemfig.tex` with kpathsea, which silently picks up your local file instead of the system package, producing a misleading `Two \documentclass commands` error. Use a different filename (e.g. `diagram.tex`) or run compiles in a clean tmpdir.

| Dependency            | Status   | Version (installed)         | ARM64 wheel source                              |
| --------------------- | -------- | --------------------------- | ----------------------------------------------- |
| `sentence-transformers` | ✅ PASS  | 5.6.0                       | PyPI (`torch 2.13.0+cu130` aarch64 wheel)       |
| `all-MiniLM-L6-v2`      | ✅ PASS  | HF Hub `sentence-transformers/all-MiniLM-L6-v2` (88 MB cached) | — |
| `rdkit`                 | ✅ PASS  | 2026.03.3                   | PyPI `manylinux_2_28_aarch64` wheel             |
| `pdflatex` + TikZ       | ✅ PASS  | pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian) | `texlive-pictures` apt package |
| `chemfig` (fallback)    | ✅ PASS  | 1.66 (2023/12/28)           | bundled in `texlive-pictures`                   |

---

## 1. `sentence-transformers` (`all-MiniLM-L6-v2`)

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install sentence-transformers
```

Pulls torch 2.13.0+cu130, transformers 5.13.0, numpy 2.5.1, scikit-learn 1.9.0, and a stack of CUDA metapackages (these are pure metadata on CPU-only ARM; no GPU is required or used). **Install time: 2m 46s on this host.**

### Smoke test

Single embedding call against `all-MiniLM-L6-v2` produces a 384-dim `float32` vector. Cosine similarity distinguishes related physics sentences (0.68) from unrelated ones (~0.06–0.12):

```
=== sentence-transformers ARM64 smoke test ===
import time: 37.86s            <- one-time torch import cost
model load time: 2.40s         <- HF Hub download + state-dict load (88 MB)
inference (3 sentences) time: 0.15s
embedding shape: (3, 384), dtype: float32
cos(v1,v2) [similar physics]: 0.6803
cos(v1,v3) [unrelated]:       0.1218
cos(v2,v3) [unrelated]:       0.0623
=== PASS ===
```

Model is cached at `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` (88 MB). Subsequent runs skip the download.

### Notes for the pipeline

- The 38 s torch import is paid once per process. For nightly batch dedup, that cost is amortized across all questions generated that night — fine.
- This host has no CUDA. Inference is CPU. For dedup over a nightly batch (~200–500 questions) at 384-dim that is well under 1 s of work; latency is not a concern.
- The model ships as `sentence-transformers/all-MiniLM-L6-v2` on HF Hub (no auth required; an unauthenticated warning is printed, not an error).

### Fallback plan (if `sentence-transformers` ever fails)

Per orchestration-review §3 and the task spec: brute-force cosine dedup using TF-IDF + scikit-learn cosine similarity. Concretely:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
vec = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
X = vec.fit_transform(question_texts)
sim = cosine_similarity(X)  # threshold at > 0.85 for near-duplicates
```

This is lexical (no semantics) so it catches only literal/near-literal dupes. Acceptable as a degraded mode; **not a substitute** for the real model. Activating the fallback requires a P0 follow-up to triage whether the model can be repaired (often: cache corruption → wipe `~/.cache/huggingface` and re-download; transformer version skew → pin `transformers==5.13.0`; ARM-build breakage → check PyTorch ARM wheels).

---

## 2. `RDKit`

### Install

```bash
pip install rdkit           # current name; rdkit-pypi is deprecated and returns 404
```

The `manylinux_2_28_aarch64` wheel is published by the RDKit core team (35.7 MB; install time 2.7 s). **No system packages required.**

### Smoke test — atom-balance check

The intended ESAT use case (orchestration-review §4, generator §3.4): verify a generated chemistry equation conserves elements. Using `Chem.MolFromSmiles` + `AddHs` to fold implicit hydrogens, then counting atoms element-wise across reactants and products:

```
Test A — balanced: 2 H2 + O2 -> 2 H2O
  ok=True, info=({'H': 4, 'O': 2}, {'O': 2, 'H': 4})
Test B — methane combustion CH4 + 2 O2 -> CO2 + 2 H2O
  ok=True, info=({'C': 1, 'H': 4, 'O': 4}, {'O': 4, 'C': 1, 'H': 4})
Test C — unbalanced (dropped one H2O)
  ok=False, info=({'C': 1, 'H': 4, 'O': 4}, {'O': 3, 'C': 1, 'H': 2})
PASS — RDKit atom-balance check works correctly
```

The check correctly accepts the balanced equations and rejects the unbalanced one. Charge and isotope balance are not in this minimal example but are available via `atom.GetFormalCharge()` / `atom.GetIsotope()`.

### Smoke test — diagram generation

`Draw.MolDraw2DSVG` produces inline SVG (4276 chars for phenol). `Draw.MolToImage` produces a 200×200 PNG. Both work without invoking any external binary — useful for headless nightly runs.

### Gotchas

- **Package rename.** `pip install rdkit-pypy` returns `ERROR: No matching distribution found for rdkit-pypi`. Use `pip install rdkit`.
- **SMILES syntax for molecules with implicit hydrogens.** Methane is `C`, not `CH4` — SMILES counts implicit Hs automatically. The atom-balance check above uses `Chem.AddHs()` to make those Hs explicit before counting. This is the correct way to compare across reactants/products where coefficients differ.
- **Stoichiometric coefficients are not in the SMILES.** `CH4 + 2 O2 -> CO2 + 2 H2O` is balanced because the *coefficients* are 1,2,1,2. To check via RDKit, either (a) repeat the SMILES per coefficient as in the test above, or (b) parse the equation string and multiply atom counts by integer coefficients before comparing. Approach (b) is what the generator should do.

### Fallback plan (if `RDKit` ever fails)

Per the task spec: use **`chemfig`-only chemistry diagrams** (no RDKit-rendered depictions) and use **manual atom counting** for stoichiometry checks. Concretely:

- For **balance checks**: parse the equation string with a small grammar (`coeff? formula ( + coeff? formula )*`), compute atom counts from formulas directly (`H2SO4 → H:2, S:1, O:4`), compare reactant vs product sums. This is ~30 lines of Python and needs no native deps. It misses cases like `CH3COOH` that need valence-aware parsing — flag those for human review.
- For **diagrams**: TikZ `chemfig` alone can draw molecules (verified in §3 below), it is just slower to author and harder to template. Use the SVG template library budget from orchestration-review §3.4 for the long tail of biology diagrams.

The fallback is a real quality regression (more false positives in balance checking, less templateable diagrams). Treat `RDKit` failure as P0.

---

## 3. `pdflatex` + TikZ (and `chemfig` fallback)

### Install

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  texlive-latex-base texlive-latex-recommended texlive-latex-extra \
  texlive-fonts-recommended texlive-pictures texlive-pstricks
```

Total ~750 MB on disk. **Install time:** ~1 minute. `pdflatex` is not on the base image — this install step must be part of the bootstrap.

### Verified available

```
$ which pdflatex                → /usr/bin/pdflatex
$ pdflatex --version | head -1  → pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian)
$ kpsewhich tikz.sty            → /usr/share/texlive/texmf-dist/tex/latex/pgf/frontendlayer/tikz.sty
$ kpsewhich pgf.sty             → .../pgf/basiclayer/pgf.sty
$ kpsewhich chemfig.sty         → .../tex/generic/chemfig/chemfig.sty   (v1.66, 2023/12/28)
```

### Smoke test — TikZ block diagram

A standalone document with three labelled boxes and arrows compiled successfully:

```
time pdflatex -interaction=nonstopmode -halt-on-error sample.tex
real    0m0.352s
sample.pdf: 1 page, 14838 bytes
```

0.35 s per compile is fast enough for inline generation, but the orchestration review recommends caching compiled PDFs by source hash to skip recompiles when the same TikZ source appears in multiple questions.

### Smoke test — chemfig (the chemistry fallback path)

```latex
\documentclass[border=2pt]{standalone}
\usepackage{chemfig}
\begin{document}
\chemfig{C(-[2]H)(-[6]H)(-[4]H)-[0]OH}
\end{document}
```

Compiles to a 11821-byte PDF showing methanol. Confirms `chemfig` is available as the diagram-rendering fallback if RDKit's depiction path ever fails.

### Source-hash caching — recommended pattern

Verified working with this implementation:

```python
import hashlib, os, subprocess, time, shutil
from pathlib import Path

CACHE_DIR = Path("var/tikz-cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def compile_tikz(src: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Return path to PDF. Recompiles only if source hash differs."""
    src_hash = hashlib.sha256(src.encode()).hexdigest()[:16]
    pdf_path = cache_dir / f"{src_hash}.pdf"
    if pdf_path.exists():
        return pdf_path                          # cache hit, ~0 ms

    work = cache_dir / f"_work_{src_hash}"
    work.mkdir(exist_ok=True)
    (work / "diagram.tex").write_text(src)       # filename must NOT be chemfig.tex
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "diagram.tex"],
            cwd=work, capture_output=True, text=True, timeout=30, check=True,
        )
        shutil.move(str(work / "diagram.pdf"), str(pdf_path))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return pdf_path
```

Test output:

```
Run 1 (cold cache):    CACHE MISS — compiled in 0.35s, saved bf25ccdea3d547c8.pdf (14838 bytes)
Run 2 (warm cache):    CACHE HIT  — bf25ccdea3d547c8.pdf (14838 bytes)
Run 3 (modified src):  CACHE MISS — compiled in 0.35s, saved 670884dde80de76a.pdf (14985 bytes)
```

Each compile runs in a per-source tmpdir; the cwd is cleaned up in a `finally` so we don't accumulate `_work_*` dirs. A 16-hex-char prefix keeps filenames filesystem-friendly; collision probability at 16 hex chars is negligible for a nightly run (well below 1 in 65k even at 10 000 diagrams).

### ⚠️ Gotcha — do not name user files `chemfig.tex`

While debugging, I had a leftover test file `chemfig.tex` in the compile working directory. `chemfig.sty` does `\input chemfig.tex` (line 2 of the system `chemfig.sty`) — kpathsea resolves that name to the file in the current directory, *not* the system `chemfig.tex`. The user file then begins with `\documentclass{...}`, which LaTeX rejects with `! LaTeX Error: Two \documentclass or \documentstyle commands.` This error is misleading — the actual cause is the input-name collision, not a real package conflict.

**Mitigation:** always name the source file something that is not a package name (`diagram.tex`, not `tikz.tex`, `chemfig.tex`, `pgf.sty`, etc.). The reference implementation above uses `diagram.tex`.

### Fallback plan (if `pdflatex`/TikZ ever fails)

Per the task spec. The TikZ path is for diagrams only; text and questions render through Next.js regardless. Failure modes:

- **pdflatex not installed:** the bootstrap script failed. Re-run the install block. Should be caught by a pre-flight check in the nightly orchestrator before generation begins.
- **TikZ compile error on a specific question:** log the source, return a placeholder diagram, mark the question for re-generation. Do not abort the batch.
- **Whole LaTeX install is broken:** pre-rendered SVG fallback for the top-N most common diagram templates (the `$200 one-time` template budget from orchestration-review §3.4). This is a degraded visual experience and should be P1 to repair.

---

## Operational recommendations for ESA-21 → ESA-24

1. **Bootstrap script** (probably lives in `shared/scripts/`) should run, in order:
   ```bash
   sudo apt-get install -y --no-install-recommends \
     texlive-latex-base texlive-latex-recommended texlive-latex-extra \
     texlive-fonts-recommended texlive-pictures
   python3 -m venv .venv && source .venv/bin/activate
   pip install sentence-transformers rdkit
   ```
   `texlive-pstricks` is optional (only needed for legacy PSTricks diagrams); skipping it saves ~150 MB.
2. **Cache directories** (set up by the bootstrap, both must be writable by the worker and persistent across runs for the cache to do its job):
   - `~/.cache/huggingface/` — model weights (88 MB, populated once)
   - `var/tikz-cache/` inside the project root — compiled PDF cache (grows ~15 KB per unique diagram)
3. **Nightly orchestrator preflight** (ESA-24) should:
   - `python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').encode(['preflight'])"` — fails fast if the HF cache was wiped.
   - `python3 -c "from rdkit import Chem; Chem.MolFromSmiles('C')"` — fails fast if RDKit wheel is broken.
   - `which pdflatex` — fails fast if TeX Live was uninstalled.
   Abort the run (and alert) if any of these fail before paying for any LLM calls.
4. **Filename hygiene in the worker:** the temp `.tex` file inside `compile_tikz` must not share a name with any installed LaTeX package. Use `diagram.tex` or `q.tex` (verified safe).
5. **Pin versions** for reproducibility:
   ```
   sentence-transformers==5.6.0
   rdkit==2026.03.3
   transformers==5.13.0
   torch==2.13.0
   ```
   TeX Live version is pinned to whatever Ubuntu ships (currently 2023.20240207-1).

## Acceptance criteria check

- ✅ Report written at `shared/arm64-deps-verification.md` (this file)
- ✅ Install commands for each dependency
- ✅ Test outputs (smoke-test transcripts) for each dependency
- ✅ Fallback plans for each dependency (only the LaTeX fallback is hypothetical — all three primary deps work)
- ✅ Each dep works on ARM64; no fallback currently needs to be activated
