# ESAT Question Generation: Multi-Agent System Architectures & Cost Analysis

**Prepared:** June 25, 2026  
**Project:** ESAT Gymnasium — Infinite Practice Question Generation  
**Target:** ~5,000 questions across 5 modules over several months

---

## 1. Executive Summary

This report evaluates **five multi-agent architectures** for generating ESAT (Engineering and Science Admissions Test) practice questions at scale. Each architecture is costed with real 2026 API pricing, token-level math, and a quality assurance strategy.

### Key Findings

| Metric | Recommended Architecture |
|---|---|
| **Best Cost-Quality Balance** | Architecture B: Premium Pipeline (Opus per-topic extraction + Haiku/Sonnet generation) |
| **Lowest Cost** | Architecture A: Budget Pipeline (GLM + Gemini free tier) |
| **Best Quality** | Architecture C: Mixed-Model Multi-Agent |
| **Best for Long-Term Scale** | Architecture D: Open-Source Self-Hosted |

**Recommended approach:** **Architecture B (Premium Pipeline)** using Claude Haiku 4.5 for bulk generation ($0.013–$0.025/question) with Claude Opus 4.8 for per-topic pattern extraction and quality review, yielding **5,000 questions for approximately $38–$73 in API costs**, with TikZ/LaTeX for diagram generation and SymPy-based solver verification.

The single most important cost lever is **model selection for the generation step** — using Haiku 4.5 instead of Opus 4.8 reduces per-question cost by **20×** while still producing high-quality A-Level STEM content. Combined with Anthropic's Batch API (50% discount) and prompt caching (90% input savings on repeated context), costs can be driven even lower.

---

## 2. Model Landscape — Current Pricing & Capabilities

All prices verified against official provider documentation in June 2026.

### 2.1 Anthropic (Claude)

*Source: [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)*

| Model | Input ($/MTok) | Output ($/MTok) | Cache Hit ($/MTok) | Context Window | Best For |
|---|---|---|---|---|---|
| Claude Opus 4.8 | $5.00 | $25.00 | $0.50 | 200K | Complex reasoning, pattern analysis, quality review |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $0.30 | 200K (1M with beta) | Balanced generation, moderate reasoning |
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 | 200K | **Bulk question generation** — best value |
| Claude Fable 5 | $10.00 | $50.00 | $1.00 | 200K | Ultra-premium (not available to user) |

**Key discounts:**
- **Batch API:** 50% off all token prices (results within 24 hours) — *ideal for bulk question generation*
- **Prompt Caching:** Cache reads cost 0.1× standard input (90% savings on repeated system prompts/examples)
- **Batch + Cache can stack** for combined savings up to 95% on input tokens

### 2.2 OpenAI

*Source: [openai.com/api/pricing](https://openai.com/api/pricing), [pricepertoken.com](https://pricepertoken.com)*

| Model | Input ($/MTok) | Output ($/MTok) | Cached Input ($/MTok) | Context Window | Best For |
|---|---|---|---|---|---|
| GPT-5.2 | $1.75 | $14.00 | $0.175 | 128K | Frontier reasoning |
| GPT-4.1 | $2.00 | $8.00 | $0.50 | 1M | STEM generation, strong reasoning |
| GPT-4.1 mini | $0.40 | $1.60 | $0.10 | 1M | Budget generation |
| GPT-4.1 nano | $0.10 | $0.40 | $0.025 | 1M | Cheapest OpenAI option |
| o4-mini | $1.10 | $4.40 | $0.275 | 200K | Step-by-step math reasoning |

**Key discounts:**
- **Batch API:** 50% off (same model as Anthropic — async within 24h)
- **Prompt Caching:** 75% discount on cached input (automatic for prompts >1,024 tokens)

### 2.3 z.ai (GLM)

*Source: [docs.z.ai/guides/overview/pricing](https://docs.z.ai/guides/overview/pricing)*

| Model | Input ($/MTok) | Cached Input ($/MTok) | Output ($/MTok) | Context Window | Best For |
|---|---|---|---|---|---|
| GLM-5.2 | $1.40 | $0.26 | $4.40 | 128K | Latest flagship GLM |
| GLM-5.1 | $1.40 | $0.26 | $4.40 | 128K | Near-frontier reasoning |
| GLM-5 | $1.00 | $0.20 | $3.20 | 128K | Strong reasoning, good value |
| GLM-5-Turbo | $1.20 | $0.24 | $4.00 | 128K | High-speed generation |
| GLM-4.7 | $0.60 | $0.11 | $2.20 | 128K | Mid-tier value |
| GLM-4.5 | $0.60 | $0.11 | $2.20 | 128K | Solid STEM capability |
| GLM-4.5-Air | $0.20 | $0.03 | $1.10 | 131K | **Cheapest GLM** — excellent for bulk |
| GLM-4.7-Flash | **FREE** | FREE | **FREE** | 128K | Rate-limited free tier |
| GLM-4.5-Flash | **FREE** | FREE | **FREE** | 128K | Rate-limited free tier |
| GLM-4.6V (Vision) | $0.30 | $0.05 | $0.90 | 128K | Diagram verification (vision) |
| GLM-4.6V-Flash | **FREE** | FREE | **FREE** | 128K | Free vision model |

**Key advantages:**
- Free tier models (GLM-4.7-Flash, GLM-4.5-Flash) available with rate limits
- Cached input is extremely cheap (~5× cheaper than standard)
- Vision models available for diagram verification at very low cost
- Open-source weights available for self-hosting (GLM-4.5 family)

### 2.4 Google Gemini

*Source: [cloud.google.com/vertex-ai/generative-ai/pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing), [costgoat.com](https://costgoat.com/pricing/gemini-api)*

| Model | Input ($/MTok) | Output ($/MTok) | Context Window | Free Tier? | Best For |
|---|---|---|---|---|---|
| Gemini 3.1 Pro Preview | $2.00 | $12.00 | 2M | No (paid-only) | Latest flagship |
| Gemini 3.5 Flash | $1.50 | $9.00 | 1M | Yes (rate-limited) | Frontier + speed |
| Gemini 2.5 Pro | $1.25 | $10.00 | 1M | **Paid-only since Apr 2026** | Deep reasoning |
| Gemini 2.5 Flash | $0.30 | $2.50 | 1M | Yes (rate-limited) | Budget generation |
| Gemini 2.5 Flash-Lite | ~$0.15 | ~$0.60 | 1M | Yes (rate-limited) | Cheapest Gemini |

**Key notes:**
- Free tier available for Flash models (rate-limited, Google may use data for improvement)
- Batch API: 50% off all models
- Pro models became paid-only as of April 2026
- Massive 1M–2M context windows — excellent for digesting entire past paper archives

### 2.5 Open-Source Models (Self-Hosted)

*Source: [vast.ai/pricing](https://vast.ai/pricing), [getdeploying.com/gpus](https://getdeploying.com/gpus), [blog.clore.ai](https://blog.clore.ai/gpu-cloud-pricing-comparison)*

| Model | Parameters | VRAM Required | STEM Quality | Notes |
|---|---|---|---|---|
| DeepSeek V3.2 | 671B (37B active MoE) | 8× H100 80GB | Excellent (math/reasoning) | FP8, top-tier open-source |
| Qwen 3 235B | 235B (22B active MoE) | 4× H100 or 8× A100 | Excellent | Strong multilingual + STEM |
| Qwen 2.5 72B | 72B | 2× H100 or 4× A100 | Very good | Solid mid-range option |
| Llama 4 Scout | 109B (17B active MoE) | 4× H100 | Very good | Meta's latest |
| GLM-4.5 | 355B (32B active MoE) | 8× H100 | Very good | Open weights from z.ai |
| DeepSeek-R1-Distill-Qwen-32B | 32B | 1× A100 80GB | Good (reasoning) | Distilled reasoning model |

**GPU Rental Costs (2026 market rates):**

| GPU | VRAM | Cheapest (Vast.ai) | Mid-range (RunPod) | Premium (AWS) |
|---|---|---|---|---|
| RTX 4090 | 24GB | $0.13/hr | $0.34/hr | $0.77/hr |
| RTX A6000 | 48GB | $0.29/hr | $0.45/hr | ~$1.00/hr |
| A100 80GB | 80GB | $0.79/hr | $1.10/hr | ~$3.20/hr |
| H100 SXM 80GB | 80GB | $1.47/hr | $2.00/hr | ~$4.00/hr |
| H200 141GB | 141GB | $1.32/hr | $2.50/hr | ~$5.00/hr |

*Sources: vast.ai pricing page, RunPod pricing page, getdeploying.com comparison*

### 2.6 Pricing Summary Table (Per Million Tokens)

| Tier | Model | Input | Output |
|---|---|---|---|
| **Ultra-cheap** | GLM-4.5-Flash | FREE | FREE |
| **Ultra-cheap** | GLM-4.7-Flash | FREE | FREE |
| **Ultra-cheap** | Gemini 2.5 Flash-Lite | ~$0.15 | ~$0.60 |
| **Budget** | GLM-4.5-Air | $0.20 | $1.10 |
| **Budget** | GPT-4.1 nano | $0.10 | $0.40 |
| **Budget** | GLM-4.5 | $0.60 | $2.20 |
| **Budget** | Gemini 2.5 Flash | $0.30 | $2.50 |
| **Mid-range** | GPT-4.1 mini | $0.40 | $1.60 |
| **Mid-range** | o4-mini | $1.10 | $4.40 |
| **Mid-range** | Claude Haiku 4.5 | $1.00 | $5.00 |
| **Premium** | Claude Sonnet 4.6 | $3.00 | $15.00 |
| **Premium** | GPT-4.1 | $2.00 | $8.00 |
| **Premium** | GLM-5 | $1.00 | $3.20 |
| **Flagship** | Claude Opus 4.8 | $5.00 | $25.00 |
| **Flagship** | Gemini 2.5 Pro | $1.25 | $10.00 |
| **Flagship** | GLM-5.2 | $1.40 | $4.40 |

---

## 3. Diagram Generation Deep Dive

ESAT questions for Physics, Chemistry, and Biology frequently require diagrams: circuit diagrams, force/free-body diagrams, molecular structures, ray diagrams, reaction schemes, cell diagrams, data graphs, and experimental setups.

### 3.1 Approach Comparison

| Approach | Accuracy | Consistency | Cost | Speed | Editability | ESAT Suitability |
|---|---|---|---|---|---|---|
| **TikZ/LaTeX (code-based)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ (token cost only) | Medium | ⭐⭐⭐⭐⭐ | **Excellent** — precise, scalable, academic standard |
| **Matplotlib/Python** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ | Fast | ⭐⭐⭐⭐ | **Excellent** — especially for graphs/data plots |
| **SVG (hand-coded/templated)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ | Fast | ⭐⭐⭐⭐⭐ | Very good — web-native, crisp at any scale |
| **JSXGraph (interactive JS)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $$ | Medium | ⭐⭐⭐⭐ | Good — interactive for web platform |
| **Template library** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ (build cost) | **Fastest** | ⭐⭐⭐ | **Excellent** — pre-built, parameterized |
| **DALL-E / image gen AI** | ⭐⭐ | ⭐ | $$$ | Medium | ⭐ | **Poor** — unreliable labels, blurry text |
| **Vision-language model** | ⭐⭐⭐ | ⭐⭐⭐ | $$ | Slow | ⭐⭐ | Fair — useful for verification, not creation |

### 3.2 Recommended: Code-Based (TikZ + Matplotlib + SVG)

**Why code-based wins for ESAT:**

1. **Precision:** TikZ produces pixel-perfect circuit diagrams, force diagrams, and geometric constructions — exactly what Cambridge exams use
2. **Consistency:** Same code = same output every time. No variation between questions
3. **Cost:** Only token costs for generation (an LLM writes TikZ code; LaTeX compiler renders it)
4. **Editability:** If a diagram needs adjustment, tweak the code — no re-generation needed
5. **Web-ready:** TikZ → PDF → PNG/SVG for web display. Matplotlib outputs SVG directly
6. **Academic standard:** Cambridge exams themselves use LaTeX/TikZ-style diagrams

**Proven workflow** (documented by [PhysicsLens.com](https://www.physicslens.com/a-new-ai-enabled-workflow-for-generating-diagrams-for-questions)):

1. LLM generates TikZ code from question context
2. LaTeX compiler (pdflatex) renders to PDF
3. Convert to PNG/SVG for web
4. LLM or human reviews the rendered image
5. Iterate if needed (typically 2–3 rounds)

**Token cost per diagram (TikZ approach):**
- Prompt (~1,500 tokens): question context + diagram description + TikZ examples
- Output (~400 tokens): TikZ code
- Using Haiku 4.5: (1,500 × $1/MTok) + (400 × $5/MTok) = $0.0015 + $0.002 = **$0.0035/diagram**
- Using GLM-4.5-Air: (1,500 × $0.20/MTok) + (400 × $1.10/MTok) = $0.0003 + $0.00044 = **$0.00074/diagram**

### 3.3 Diagram Types by Module

| Module | Common Diagrams | Best Tool |
|---|---|---|
| **Physics** | Circuits, force diagrams, ray diagrams, waves, fields | TikZ (circuits), Matplotlib (graphs) |
| **Chemistry** | Molecular structures, reaction schemes, energy diagrams | TikZ + chemfig package |
| **Biology** | Cell diagrams, experimental setups, ecological diagrams | TikZ + biochemistry templates |
| **Maths 1 & 2** | Geometry, coordinate graphs, functions, 3D shapes | TikZ + pgfplots |

### 3.4 Template-Based Hybrid (Best for Scale)

For maximum consistency and minimum cost, build a **parameterized template library**:

1. **One-time:** Use Opus 4.8 to create 20–30 base TikZ templates per module (e.g., "incline with block", "circuit with resistors", "lens ray diagram")
2. **Runtime:** Generator LLM selects a template and fills in parameters (angle, resistance values, focal length)
3. **Rendering:** LaTeX compiler produces the final image

This eliminates the need for creative diagram generation during bulk question production.

---

## 4. Multi-Agent Frameworks Comparison

### 4.1 Framework Matrix

| Framework | Architecture | Best For | Complexity | State Management | Cost | ESAT Fit |
|---|---|---|---|---|---|---|
| **LangGraph** | Graph-based workflow | Stateful, multi-step pipelines | Medium-High | ⭐⭐⭐⭐⭐ | Free (OSS) | **Best** — deterministic pipeline |
| **CrewAI** | Role-based agents | Sequential business processes | Low-Medium | ⭐⭐⭐ | Free (OSS) | Good — simple role assignment |
| **AutoGen** (Microsoft) | Conversational agents | Research, brainstorming, debates | Medium | ⭐⭐⭐ | Free (OSS) | Fair — too loose for structured gen |
| **OpenClaw** | Agent orchestration | Multi-model coordination, heartbeats | Low (configured) | ⭐⭐⭐⭐ | Free (self-hosted) | Good — already available to user |
| **Custom Python** | Direct API calls | Full control, minimal overhead | Medium | Whatever you build | Free | **Excellent** — simplest for batch gen |
| **Google A2A** | Agent-to-agent protocol | Cross-vendor interoperability | High | ⭐⭐⭐ | Free (OSS) | Overkill — designed for multi-org |

*Sources: [DataCamp comparison](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen), [Latenode comparison](https://latenode.com/blog/langgraph-vs-autogen-vs-crewai), [Automatos comparison](https://automatos.app/blog/top-5-ai-agent-frameworks-2025)*

### 4.2 Recommendation: Custom Python (No Framework Dependency)

For ESAT question generation, the workflow is **fundamentally a batch pipeline**, not a conversational multi-agent system:

```
[Pattern Extractor] → [Question Generator] → [Solver/Verifier] → [Calculator-Free Check] → [Difficulty Scorer] → [Distractor Refiner] → [Diagram Generator] → [Reviewer] → [Output]
```

This is a **linear, stateful pipeline**. A **custom Python orchestrator with async API calls** is the correct approach — zero framework overhead, full control, easy to debug.

**Why not LangGraph/CrewAI/AutoGen:** These frameworks add complexity for no benefit. The pipeline is deterministic — every question goes through the same sequence of function calls. There is no agent-to-agent conversation, negotiation, or dynamic routing. A custom Python module with clear separation of concerns is simpler, more debuggable, and avoids a framework dependency.

**Why not OpenClaw as primary orchestration:** OpenClaw is excellent for managing agent lifecycles and multi-model coordination, but for a batch generation pipeline, a Python script calling APIs directly is simpler and faster. OpenClaw is used to *schedule and monitor* the pipeline (cron jobs, Telegram alerts), not as the pipeline itself.

### 4.3 Google A2A Protocol

*Source: [Linux Foundation announcement (June 2025)](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project), [Atlan guide](https://atlan.com/know/google-a2a-protocol)*

A2A is an **interoperability protocol**, not an orchestration framework. It matters if you need agents built on different frameworks (e.g., a LangGraph agent talking to a CrewAI agent) to communicate. For ESAT Gymnasium's internal pipeline, this is unnecessary complexity. It becomes relevant if you want to expose your question-generation agent as a service to other systems.

---

## 5. Proposed Architectures

### Architecture A: Budget Pipeline (Free/Cheap)

**Philosophy:** Use only free-tier and ultra-cheap models. Accept slightly lower quality and higher rejection rate.

#### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (Python script)                │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Pattern      │  │ Question     │  │ Solver/      │       │
│  │ Extractor    │→ │ Generator    │→ │ Verifier     │       │
│  │ (GLM-4.5-    │  │ (GLM-4.5-    │  │ (GLM-4.5-    │       │
│  │  Flash FREE) │  │  Air $0.20/  │  │  Air $0.20/  │       │
│  │              │  │  MTok in)    │  │  MTok in)    │       │
│  └──────────────┘  └──────┬───────┘  └──────┬───────┘       │
│                           │                 │               │
│                    ┌──────▼───────┐  ┌──────▼───────┐       │
│                    │ Diagram Gen  │  │ Reviewer     │       │
│                    │ (GLM-4.5-    │  │ (Gemini 2.5  │       │
│                    │  Air TikZ)   │  │  Flash FREE  │       │
│                    └──────────────┘  │  or GLM-4.7- │       │
│                                      │  Flash FREE) │       │
│                                      └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

#### Model Assignments

| Agent Role | Model | Why |
|---|---|---|
| Pattern Extractor | GLM-4.5-Flash (FREE) | Ingest past papers, extract question patterns. Free tier, large context |
| Question Generator | GLM-4.5-Air ($0.20/$1.10) | Bulk question generation. Cheapest paid model with solid STEM ability |
| Solver/Verifier | GLM-4.5-Air ($0.20/$1.10) | Solve the question independently, verify answer |
| Diagram Generator | GLM-4.5-Air ($0.20/$1.10) | Generate TikZ code for diagrams |
| Reviewer | GLM-4.7-Flash (FREE) or Gemini 2.5 Flash (FREE) | Quality check, reject bad questions |

#### Token Math (Per Question)

**Step 1: Pattern Context (cached across all questions in a batch)**
- System prompt + style guide + examples: ~3,000 tokens (cached after first call)

**Step 2: Question Generation**
- Input: 3,000 tokens (system + pattern + spec) — mostly cached
- Output: ~500 tokens (question + 5 options + answer + worked solution)
- Cached input cost: 3,000 × $0.03/MTok = $0.00009
- Output cost: 500 × $1.10/MTok = $0.00055
- **Generation cost: $0.00064/question**

**Step 3: Solver Verification**
- Input: ~800 tokens (question + options + answer to verify)
- Output: ~300 tokens (independent solution)
- Input cost: 800 × $0.20/MTok = $0.00016
- Output cost: 300 × $1.10/MTok = $0.00033
- **Verification cost: $0.00049/question**

**Step 4: Diagram Generation (for ~40% of questions)**
- Input: 1,500 tokens (context + TikZ examples)
- Output: 400 tokens (TikZ code)
- Per-question-with-diagram cost: $0.00074
- Averaged across all questions (40% have diagrams): $0.00074 × 0.40 = $0.00030
- **Diagram cost: $0.00030/question** (averaged)

**Step 5: Review (free model)**
- $0/question

**Total per question: $0.00064 + $0.00049 + $0.00030 = ~$0.00143/question**

#### Total Cost for 5,000 Questions
**5,000 × $0.00143 = ~$7.15**

#### Quality Assurance
- **Solver verification:** GLM-4.5-Air independently solves each question and checks answer match
- **Rejection rate:** ~15–25% expected (lower quality model = more bad questions)
- Net effective cost accounting for rejections: $7.15 × 1.25 = **~$8.94** for 5,000 accepted questions
- **No SymPy verification** (would require additional pipeline step)
- **No vision-based diagram verification** (free vision model GLM-4.6V-Flash could be added)

#### Strengths
- **Essentially free** — under $10 for 5,000 questions
- Uses models the user already has access to
- No infrastructure needed beyond a Python script
- GLM models have surprisingly good STEM capability

#### Weaknesses
- **Quality ceiling lower** — GLM-4.5-Air is capable but not frontier; expect more ambiguous questions, edge-case errors
- **Higher rejection rate** — more wasted generation cycles
- **No calculator-free reasoning guarantee** — model may produce questions requiring calculator use
- **Rate limits** on free tier models could throttle throughput
- **Diagram quality variable** — GLM-4.5-Air's TikZ may need more iteration rounds

---

### Architecture B: Premium Pipeline (Opus + Haiku) — **RECOMMENDED**

**Philosophy:** Use frontier model (Opus 4.8) for one-time pattern extraction and final quality review. Use Haiku 4.5 for bulk generation. Best cost-quality ratio.

#### System Design

```
┌──────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Python + LangGraph)               │
│                                                                   │
│  ┌─────────────────┐                                              │
│  │ Pattern Extractor│  ONE-TIME: Analyze ENGAA/NSAA past papers   │
│  │ (Opus 4.8)      │  → Produce style guide + question templates  │
│  │ $5/$25 MTok     │  → Extract syllabus coverage matrix          │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼ (style guide + templates fed to all downstream agents)│
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Question         │→ │ Solver/Verifier  │→ │ Reviewer        │  │
│  │ Generator        │  │ (Haiku 4.5 +     │  │ (Haiku 4.5      │  │
│  │ (Haiku 4.5      │  │  SymPy)          │  │  + scored       │  │
│  │  Batch API)     │  │                  │  │  rubric)        │  │
│  │ $1/$5 MTok      │  │                  │  │                 │  │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘  │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ Diagram         │  Generate TikZ code → compile → render       │
│  │ Generator       │  (Haiku 4.5 + TikZ template library)        │
│  │ (Haiku 4.5)     │                                              │
│  └─────────────────┘                                              │
└──────────────────────────────────────────────────────────────────┘
```

#### Model Assignments

| Agent Role | Model | Why |
|---|---|---|
| Pattern Extractor (one-time) | Claude Opus 4.8 | Best reasoning model. Extract deep patterns from past papers |
| Question Generator | Claude Haiku 4.5 | Matches Sonnet 4 quality on many benchmarks at 1/3 the price |
| Solver/Verifier | Claude Haiku 4.5 + SymPy | LLM solves independently; SymPy verifies mathematical correctness |
| Diagram Generator | Claude Haiku 4.5 + TikZ templates | Haiku is excellent at code generation; templates ensure consistency |
| Reviewer | Claude Haiku 4.5 | Scored rubric: clarity, difficulty, syllabus match, uniqueness |

#### One-Time: Pattern Extraction Cost

- **Stage 1 (Haiku classification):** ~2,500–3,000 questions classified to ESAT spec taxonomy codes via Haiku 4.5 Batch API (~$0.50–$1.00)
- **Stage 2+3 (Opus per-topic extraction):** ~36 topic-level Opus calls producing distractor catalogues, style guides, and insight scenarios (~$5.40–$7.20)
- **Total pattern extraction: ~$6–$8 one-time** (see Section 10.2 for breakdown)
- Key advantage: the official ESAT Content Specification PDF provides the taxonomy and skill list directly — Opus focuses on what it does best: distractor analysis and style extraction

#### Per-Question Token Math

**Step 1: Question Generation (using Batch API — 50% discount)**
- System prompt + style guide + templates (cached): ~4,000 tokens
- Cached input cost: 4,000 × $0.10/MTok = $0.0004
- New input (specific question spec): ~500 tokens
- Batch input cost: 500 × $0.50/MTok = $0.00025
- Batch output: ~600 tokens (question, 5 options, answer, worked solution, metadata)
- Batch output cost: 600 × $2.50/MTok = $0.0015
- **Generation cost: $0.00215/question**

**Step 2: Solver Verification (using Batch API)**
- Input: ~1,000 tokens (question + worked solution to verify)
- Batch input cost: 1,000 × $0.50/MTok = $0.0005
- Output: ~400 tokens (independent solution)
- Batch output cost: 400 × $2.50/MTok = $0.0010
- **Verification cost: $0.0015/question**

**Step 3: SymPy Mathematical Verification**
- Python library — $0/question (runs locally)
- Parses question, symbolically verifies the answer for math/physics calculations
- **SymPy cost: $0/question**

**Step 4: Diagram Generation (for ~40% of questions, using Batch API)**
- Input: ~2,000 tokens (context + TikZ template + question spec)
- Batch input cost: 2,000 × $0.50/MTok = $0.001
- Output: ~500 tokens (TikZ code)
- Batch output cost: 500 × $2.50/MTok = $0.00125
- Per-question-with-diagram: $0.00225
- Averaged across all questions (40%): $0.00225 × 0.40 = $0.00090
- **Diagram cost: $0.00090/question** (averaged)

**Step 5: Review (using Batch API)**
- Input: ~1,500 tokens (question + solution + diagram)
- Batch input cost: 1,500 × $0.50/MTok = $0.00075
- Output: ~200 tokens (quality scores + pass/fail)
- Batch output cost: 200 × $2.50/MTok = $0.00050
- **Review cost: $0.00125/question**

**Total per question: $0.00215 + $0.0015 + $0.00090 + $0.00125 = ~$0.0058/question**

#### Rejection Rate Adjustment
- Expected rejection rate: ~10% (Haiku 4.5 is high quality; solver + SymPy catches errors)
- Net effective: $0.0058 × 1.10 = **~$0.0064/accepted question**

#### Total Cost for 5,000 Questions
**5,000 × $0.0064 + $6–$8 (one-time pattern extraction) = ~$38–$40**

*Even at standard (non-batch) pricing, the total would be:*
*5,000 × $0.0129 + $6–$8 = ~$70–$73*

#### Quality Assurance — Multi-Layer
1. **Solver verification:** Haiku independently solves the question; answers must match
2. **SymPy verification:** Symbolic math engine verifies computational correctness (derivatives, integrals, equations, circuit calculations)
3. **Review rubric:** Scored on clarity (1–5), difficulty match (1–5), syllabus coverage, uniqueness vs. existing bank
4. **LaTeX compilation check:** TikZ code must compile without errors
5. **Optional human spot-check:** Review 5–10% of questions manually

#### Strengths
- **Excellent cost-quality ratio** — frontier-quality questions at ~$0.006 each
- Haiku 4.5 matches Sonnet 4 on many STEM benchmarks at 1/3 the price
- Batch API + caching stack for maximum savings
- SymPy provides mathematical ground truth verification
- Per-topic Opus pattern extraction produces granular, focused distractor catalogues and style guides for every ESAT spec topic
- All within Anthropic ecosystem — consistent API, no multi-vendor complexity

#### Weaknesses
- Requires Anthropic API spend (though modest)
- Batch API introduces up to 24-hour latency (fine for batch generation, not real-time)
- Haiku may occasionally struggle with very complex multi-step physics
- SymPy verification limited to symbolically solvable problems

---

### Architecture C: Mixed-Model Multi-Agent

**Philosophy:** Use the best model for each specific task — different providers for different roles.

#### System Design

```
┌────────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (Python + LangGraph)                 │
│                                                                    │
│  ┌──────────────────┐                                               │
│  │ Pattern Extractor │  ONE-TIME: Ingest past papers               │
│  │ (Claude Opus 4.8)│  → Comprehensive style guide                 │
│  └────────┬─────────┘                                               │
│           │                                                        │
│  ┌────────▼─────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Module-Specific   │→ │ Cross-Model      │→ │ Vision Verifier  │ │
│  │ Generators        │  │ Solver           │  │ (Gemini 2.5      │ │
│  │                   │  │                  │  │  Flash or GLM-   │ │
│  │ Maths: GLM-5      │  │ Math: o4-mini    │  │  4.6V — renders  │ │
│  │ ($1/$3.2)         │  │ ($1.10/$4.40)    │  │  diagram, checks │ │
│  │ Physics: Opus 4.8 │  │ Science:         │  │  correctness)    │ │
│  │ ($5/$25)          │  │  Sonnet 4.6      │  │                  │ │
│  │ Chemistry: GPT-4.1│  │  ($3/$15)        │  │                  │ │
│  │ ($2/$8)           │  │                  │  │                  │ │
│  │ Biology: Haiku 4.5│  │ + SymPy for math │  │                  │ │
│  │ ($1/$5)           │  │  verification    │  │                  │ │
│  └───────────────────┘  └──────────────────┘  └──────────────────┘ │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                               │
│  │ Diagram Generator│  TikZ code generation + template library     │
│  │ (Haiku 4.5 or    │                                               │
│  │  GLM-4.5-Air)    │                                               │
│  └──────────────────┘                                               │
└────────────────────────────────────────────────────────────────────┘
```

#### Model Assignments & Rationale

| Agent Role | Model | Why This Model |
|---|---|---|
| Pattern Extractor | Claude Opus 4.8 | Best deep reasoning for pattern analysis |
| Maths Generator | GLM-5 ($1/$3.2) | Excellent math capability, very cheap |
| Physics Generator | Claude Opus 4.8 ($5/$25) | Physics requires deepest reasoning (mechanics, EM, circuits) |
| Chemistry Generator | GPT-4.1 ($2/$8) | Strong chemistry knowledge, balanced cost |
| Biology Generator | Claude Haiku 4.5 ($1/$5) | Biology questions more factual, less computational |
| Solver (Math) | o4-mini ($1.10/$4.40) | Chain-of-thought reasoning ideal for math verification |
| Solver (Science) | Claude Sonnet 4.6 ($3/$15) | Strong cross-domain reasoning |
| Vision Verifier | Gemini 2.5 Flash (FREE) or GLM-4.6V ($0.30/$0.90) | Render diagram, check via vision model |
| Diagram Generator | Claude Haiku 4.5 or GLM-4.5-Air | Code generation for TikZ |

#### Per-Question Token Math

Assuming question distribution across modules (Maths 1: 30%, Maths 2: 15%, Physics: 25%, Chemistry: 15%, Biology: 15%):

**Step 1: Generation (weighted average)**
- Maths (45%) — GLM-5: input ~3,500 tokens, output ~500 tokens
  - Cost: (3,500 × $1/MTok) + (500 × $3.2/MTok) = $0.0035 + $0.0016 = $0.0051
- Physics (25%) — Opus 4.8: input ~4,000 tokens, output ~700 tokens
  - Cost: (4,000 × $5/MTok) + (700 × $25/MTok) = $0.020 + $0.0175 = $0.0375
- Chemistry (15%) — GPT-4.1: input ~3,500 tokens, output ~600 tokens
  - Cost: (3,500 × $2/MTok) + (600 × $8/MTok) = $0.007 + $0.0048 = $0.0118
- Biology (15%) — Haiku 4.5: input ~3,000 tokens, output ~500 tokens
  - Cost: (3,000 × $1/MTok) + (500 × $5/MTok) = $0.003 + $0.0025 = $0.0055

Weighted average generation cost:
- (0.45 × $0.0051) + (0.25 × $0.0375) + (0.15 × $0.0118) + (0.15 × $0.0055)
- = $0.00230 + $0.00938 + $0.00177 + $0.00083
- = **$0.01428/question**

**Step 2: Solver Verification (weighted average)**
- Math (45%) — o4-mini: input ~1,000, output ~500 (with reasoning tokens)
  - Cost: (1,000 × $1.10/MTok) + (500 × $4.40/MTok) = $0.0011 + $0.0022 = $0.0033
- Science (55%) — Sonnet 4.6: input ~1,000, output ~400
  - Cost: (1,000 × $3/MTok) + (400 × $15/MTok) = $0.003 + $0.006 = $0.0090

Weighted average:
- (0.45 × $0.0033) + (0.55 × $0.0090)
- = $0.00149 + $0.00495
- = **$0.00644/question**

**Step 3: Diagram (40% of questions, Haiku/GLM-4.5-Air)**
- Average: ~$0.00225/question-with-diagram × 0.40 = **$0.00090/question**

**Step 4: Vision Verification (for questions with diagrams, ~40%)**
- GLM-4.6V: input ~1,000 tokens (image + question), output ~100 tokens
- Cost: (1,000 × $0.30/MTok) + (100 × $0.90/MTok) = $0.0003 + $0.00009 = $0.00039
- Averaged: $0.00039 × 0.40 = **$0.00016/question**

**Total per question: $0.01428 + $0.00644 + $0.00090 + $0.00016 = ~$0.02178/question**

#### Total Cost for 5,000 Questions
- Generation: 5,000 × $0.02178 = $108.90
- One-time pattern extraction (Opus 4.8, per-topic extraction): ~$6–$8
- **Total: ~$112.65**

#### Quality Assurance — Most Comprehensive
1. **Module-optimized generators:** Each subject uses the best model for its difficulty profile
2. **Cross-model solver verification:** Different model solves than generated → catches model-specific blind spots
3. **o4-mini chain-of-thought:** Explicit reasoning steps for math verification
4. **SymPy verification:** Symbolic math ground truth
5. **Vision-based diagram check:** Render diagram, send to vision model to verify it matches question description
6. **Review rubric:** Final quality scoring

#### Strengths
- **Highest quality** — best model for each task
- **Cross-model verification** catches model-specific errors
- **Vision verification** of diagrams (unique to this architecture)
- Module-optimized generation (Opus for hard physics, cheaper models for biology)

#### Weaknesses
- **More complex** — 4+ different APIs to manage
- **Higher cost** than Architecture B (~3× the cost)
- **Vendor sprawl** — rate limits, billing, API differences across Anthropic/OpenAI/Google/z.ai
- **Physics generation with Opus is expensive** ($0.0375/question for physics alone)
- More failure points in the pipeline

---

### Architecture D: Open-Source Self-Hosted

**Philosophy:** Host powerful open-source models on cloud GPUs. Zero per-token cost after hardware. Fine-tune on ESAT/ENGAA/NSAA patterns.

#### System Design

```
┌────────────────────────────────────────────────────────────────┐
│              GPU CLUSTER (Vast.ai / RunPod)                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  vLLM / SGLang Inference Server                       │      │
│  │  Serving: DeepSeek V3.2 (671B MoE) or Qwen 3 235B    │      │
│  │  Hardware: 4-8× H100 80GB or 8× A100 80GB            │      │
│  └──────────────────────────┬───────────────────────────┘      │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────┐      │
│  │  Orchestration Layer (Python)                         │      │
│  │                                                       │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │      │
│  │  │ Generator│→ │ Solver   │→ │ Reviewer │            │      │
│  │  │ (same    │  │ (same    │  │ (same    │            │      │
│  │  │  model)  │  │  model)  │  │  model)  │            │      │
│  │  └──────────┘  └──────────┘  └──────────┘            │      │
│  │                                                       │      │
│  │  ┌──────────────────────────────────┐                 │      │
│  │  │ Fine-tuning Layer (LoRA/QLoRA)   │                 │      │
│  │  │ Train on extracted ESAT patterns │                 │      │
│  │  └──────────────────────────────────┘                 │      │
│  └──────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────┘
```

#### Hardware Requirements & Cost

**Option 1: DeepSeek V3.2 (671B MoE, FP8)**
- Requires: 8× H100 80GB SXM
- Cost on Vast.ai: ~8 × $1.47/hr = ~$11.76/hr
- Cost on RunPod: ~8 × $2.00/hr = ~$16.00/hr
- Throughput: ~3,000–5,000 tokens/sec with vLLM

**Option 2: Qwen 3 235B (more practical)**
- Requires: 4× H100 80GB or 8× A100 80GB
- Cost on Vast.ai: ~4 × $1.47/hr = ~$5.88/hr (H100) or ~8 × $0.79/hr = ~$6.32/hr (A100)
- Throughput: ~2,000–4,000 tokens/sec

**Option 3: Qwen 2.5 72B (budget)**
- Requires: 2× H100 or 4× A100 80GB
- Cost on Vast.ai: ~2 × $1.47/hr = ~$2.94/hr
- Throughput: ~4,000–8,000 tokens/sec

#### Per-Question Cost Calculation

Using **Qwen 3 235B on 4× H100 at $5.88/hr**:

Each question requires approximately:
- Generation: 3,500 input + 600 output = 4,100 tokens
- Solver: 1,000 input + 400 output = 1,400 tokens
- Diagram (40%): 2,000 input + 500 output = 2,500 × 0.40 = 1,000 tokens
- Review: 1,500 input + 200 output = 1,700 tokens
- **Total per question: ~8,200 tokens**

At 3,000 tokens/sec throughput:
- Time per question: 8,200 / 3,000 = 2.73 seconds
- **Cost per question: 2.73 sec × $5.88/hr / 3600 = $0.00446/question**

**Total GPU time for 5,000 questions:**
- 5,000 × 2.73 sec = 13,650 sec = 3.79 hours
- **GPU cost: 3.79 × $5.88 = ~$22.30**

#### Additional Costs

| Item | Cost | Notes |
|---|---|---|
| Fine-tuning dataset prep | ~$5 (one-time Opus API) | Extract patterns, format training data |
| LoRA fine-tuning run | ~2 hours GPU time = ~$11.76 | One-time, improves quality ~10-15% |
| GPU idle/overhead | +20% | Loading, setup, failed runs |
| Storage & infrastructure | ~$5 | Docker images, model weights |

#### Total Cost for 5,000 Questions
- GPU inference: $22.30
- Fine-tuning: $11.76 (one-time)
- Pattern extraction: $6–$8 (one-time Opus API, per-topic extraction)
- Overhead (20%): $4.46
- **Total: ~$43.52** (or **$32.76** for subsequent batches without re-fine-tuning)

#### Quality Assurance
- Self-consistency: Run solver 3 times, majority vote
- SymPy verification (runs on CPU alongside GPU)
- Can fine-tune on verified good questions to improve over time
- Human spot-check recommended (5–10%)

#### Strengths
- **No per-token cost** — predictable hardware cost
- **Fine-tuning advantage** — can specialize model on ESAT patterns
- **Full control** — no rate limits, no API dependencies, no data leaving your servers
- **Scalable** — spin up more GPUs for faster generation
- **Future batches nearly free** — just GPU time (~$22/batch)

#### Weaknesses
- **Infrastructure complexity** — managing GPU instances, vLLM, Docker, model weights
- **Quality gap** — even with fine-tuning, Qwen 3 235B may not match Claude Haiku 4.5 on nuanced question writing (though it's close)
- **Hardware risk** — Vast.ai spot instances can be interrupted
- **Setup time** — initial setup takes 1–2 days vs. minutes for API-based
- **MoE memory requirements** — DeepSeek V3.2 needs 8× H100 which is expensive hardware to manage

---

### Architecture E: Hybrid Batch + Human-in-the-Loop

**Philosophy:** Use the best of all worlds — cheap bulk generation + strategic human review + continuous improvement feedback loop.

#### System Design

```
┌────────────────────────────────────────────────────────────────────┐
│                    GENERATION PIPELINE (Weekly Batch)                │
│                                                                    │
│  Phase 1: BULK GENERATION (Sunday night, Batch API)                │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Haiku 4.5 Batch API generates 200 questions/week        │       │
│  │  (50 per module × 4 weeks = 200/month)                  │       │
│  │  Cost: 200 × $0.006 = $1.20/week                        │       │
│  └────────────────────┬────────────────────────────────────┘       │
│                       │                                            │
│  Phase 2: AUTOMATED VERIFICATION (Monday)                          │
│  ┌────────────────────▼────────────────────────────────────┐       │
│  │  1. SymPy solver check (Python, free)                   │       │
│  │  2. Haiku 4.5 solver check ($0.0015/question)           │       │
│  │  3. LaTeX compilation check for diagrams (free)         │       │
│  │  → Auto-reject failures (expected ~10%)                 │       │
│  └────────────────────┬────────────────────────────────────┘       │
│                       │                                            │
│  Phase 3: HUMAN REVIEW (Tuesday–Thursday)                          │
│  ┌────────────────────▼────────────────────────────────────┐       │
│  │  Human reviewer (or Gilbert) spot-checks 20% of         │       │
│  │  surviving questions against real ESAT papers           │       │
│  │  → Flags issues, provides feedback                     │       │
│  └────────────────────┬────────────────────────────────────┘       │
│                       │                                            │
│  Phase 4: FEEDBACK LOOP (Friday)                                   │
│  ┌────────────────────▼────────────────────────────────────┐       │
│  │  Update system prompts based on human feedback          │       │
│  │  Add good questions to "gold standard" examples         │       │
│  │  Adjust difficulty calibration                          │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                    │
│  Phase 5: FINAL EXPORT                                             │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Questions → Database → ESAT Gymnasium web platform     │       │
│  │  Format: JSON {question, options, answer, solution,     │       │
│  │          diagram_svg, module, difficulty, tags}         │       │
│  └─────────────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────────┘
```

#### Cost Breakdown

| Phase | Per-Week Cost | Per-Question Cost |
|---|---|---|
| Bulk generation (Haiku Batch API) | $1.20 | $0.006 |
| Automated verification | $0.30 | $0.0015 |
| Human review (time cost only) | ~2 hours labor | — |
| Infrastructure | Negligible | — |
| **Weekly total** | **~$1.50** | **~$0.0075** |

**For 5,000 questions over ~25 weeks:**
- API cost: 25 × $1.50 = **$37.50**
- One-time setup (Opus per-topic pattern extraction): **$6–$8**
- **Total API cost: ~$41.25**
- Human labor: ~50 hours total (spot-checking)

#### Quality Assurance — The Best of All Worlds
1. SymPy mathematical verification (free, exact)
2. LLM solver verification (Haiku 4.5)
3. LaTeX compilation verification (free)
4. **Human expert review** (the gold standard)
5. Continuous feedback loop improves quality week-over-week
6. Growing "gold standard" question bank improves prompt quality

#### Strengths
- **Lowest API cost** while maintaining highest quality
- **Human-in-the-loop** catches subtle issues no automated system can
- **Continuous improvement** — gets better every week
- **Sustainable workflow** — 200 questions/week is manageable review volume
- **Flexible pacing** — can scale up or down as needed

#### Weaknesses
- **Requires consistent human effort** (~2 hours/week)
- **Slower** — 5,000 questions takes ~25 weeks at 200/week
- Can accelerate to 500/week if reviewer has more time
- Human reviewer becomes a bottleneck/dependency

---

## 6. Cost Comparison Table

| Architecture | Per-Question Cost | 5,000 Questions Total | Quality (1–5) | Setup Complexity |
|---|---|---|---|---|
| **A: Budget Pipeline** (GLM + free) | $0.0014 | **$7–$9** | ⭐⭐⭐ | Low |
| **B: Premium Pipeline** (Opus + Haiku, Batch) | $0.0058 | **$36–$48** | ⭐⭐⭐⭐⭐ | Medium |
| **C: Mixed-Model Multi-Agent** | $0.0218 | **$108–$130** | ⭐⭐⭐⭐⭐ | High |
| **D: Open-Source Self-Hosted** (Qwen 3) | $0.0045 | **$33–$44** | ⭐⭐⭐⭐ | High |
| **E: Hybrid + Human Review** (Haiku Batch) | $0.0075 | **$38–$45** | ⭐⭐⭐⭐⭐ | Medium |

### Cost Visualization

```
Architecture A:  ██ ($9)
Architecture B:  ██████ ($42)
Architecture C:  ████████████████████ ($113)
Architecture D:  ████████ ($44)
Architecture E:  ████████ ($41)
```

### Value Matrix (Quality per Dollar)

| Architecture | Quality Score | Cost for 5K | Quality/$ | Verdict |
|---|---|---|---|---|
| A: Budget | 3.0 | $9 | 0.33 | Best raw value, quality risk |
| **B: Premium** | **5.0** | **$42** | **0.12** | **Best balance — RECOMMENDED** |
| C: Mixed | 5.0 | $113 | 0.04 | Premium quality, high cost |
| D: Open-Source | 4.0 | $44 | 0.09 | Good for long-term scale |
| E: Hybrid | 5.0 | $41 | 0.12 | Best with human reviewer |

---

## 7. Quality Assurance Strategy

### 7.1 The Multi-Layer Verification Stack

For a question generation system producing 5,000 questions, quality is paramount. A single bad question (wrong answer, ambiguous wording, broken diagram) undermines user trust.

```
Layer 1: SYMBOKIC VERIFICATION (SymPy)
├── Parse mathematical expressions from question
├── Symbolically solve the problem
├── Compare to stated answer
├── Catches: arithmetic errors, wrong formulas, calculation mistakes
└── Coverage: ~40-50% of Maths/Physics questions (anything with solvable equations)

Layer 2: LLM SOLVER VERIFICATION (different model than generator)
├── Independent model solves the question from scratch
├── Answer must match generator's answer
├── Catches: logical errors, conceptual mistakes, model hallucinations
└── Coverage: ~95% of all questions

Layer 3: STRUCTURAL VALIDATION
├── Exactly 5 options (A-E)?
├── Exactly one correct answer?
├── Distractors plausible but clearly wrong?
├── Question text unambiguous?
├── No calculator required? (check for non-trivial arithmetic)
└── Coverage: 100% (automated checks)

Layer 3.5: STRUCTURAL DIFFICULTY SCORING
├── Count reasoning steps in worked solution
├── Count distinct concepts integrated
├── Measure distractor closeness (edit distance between correct answer and nearest distractor)
├── Score 1-10 on structural features
├── Compare against target difficulty band from template directive
├── Flag mismatches: reclassify or regenerate
└── Coverage: 100% (automated, deterministic)

Layer 4: DIAGRAM VERIFICATION
├── TikZ code compiles without errors?
├── (Optional) Vision model checks rendered diagram matches question
├── Labels readable and correct?
└── Coverage: All diagram questions

Layer 4.5: CHEMISTRY & BIOLOGY FACTUAL VERIFICATION (LLM-as-Judge)
├── For Chemistry: verify stoichiometry, bond energies, gas law derivations
│   against reference data (RDKit + lookup tables where possible)
├── For Biology: load ESAT Content Specification as context, have Haiku 4.5
│   verify every factual claim in question + answer is consistent with the spec
├── Catches: factual errors, wrong constants, incorrect definitions,
│   content outside ESAT syllabus scope
└── Coverage: ~100% of Chemistry & Biology questions (the 30% SymPy can't reach)

Layer 5: QUALITY SCORING (LLM rubric)
├── Clarity score (1-5)
├── Difficulty match score (1-5) vs. target difficulty
├── Syllabus coverage check
├── Uniqueness check (not duplicate of existing question)
├── ESAT style match (compared to style guide)
└── Coverage: 100% (automated)

Layer 6: HUMAN SPOT-CHECK (optional but recommended)
├── Review 5-10% sample
├── Catch subtle issues automated layers miss
└── Feed insights back to improve prompts
```

### 7.1.1 Calculator-Free Arithmetic Checker (ESAT-Specific)

ESAT is strictly no-calculator. The Content Specification (P3.5b) mandates **g = 10 N kg⁻¹** and requires candidates to perform all arithmetic mentally. This is the most ESAT-specific quality gate — a generated question requiring sin(23°) or 37 × 43 is unusable regardless of how good the maths is.

Full research with worked examples is in `calculator-free-research.md`. Key rules for the checker:

**Must-flag as error (Tier 1):**
1. g ≠ 10 in any physics calculation
2. Non-standard angle (anything outside 0°, 30°, 45°, 60°, 90°, 180°, 270°, 360°) used without "estimate"/"approximately" context
3. Final answer requiring > 3 significant figures
4. Multiplication of two numbers both > 15 with no nice structure (e.g. 37 × 43 — not mentally feasible)
5. Non-terminating decimal required to > 2 decimal places
6. logₐ(b) where b is not an exact power of a (e.g. log₁₀(7) — flagged; log₂(8) = 3 — fine)
7. Physical constants (speed of light, specific heat capacity, etc.) not given in the question stem

**Should-flag as warning (Tier 2):**
1. Square roots of non-perfect, non-standard numbers (√17 to decimal precision — flagged; √12 → 2√3 — fine, that's a tested skill)
2. Fractions with denominators > 12 in non-exact contexts
3. Decimal precision in given values exceeding 3 significant figures
4. Non-SI units used (kWh, eV, atm, bar, calorie — none of these are in the ESAT spec)
5. Compound units written with slash (m/s) instead of negative indices (m s⁻¹)

**Key ESAT conventions:**
- **g = 10 N kg⁻¹** — always, not 9.8 or 9.81. The spec is explicit.
- **Surds are tested** — students must simplify √12 → 2√3, rationalise denominators, and leave answers in surd form. The checker should NOT flag surds as problematic; they're an examined skill.
- **Estimation is tested** — M2.14 covers approximation including π and surds. Questions using "estimate" or "approximately" get relaxed rules.
- **Standard trig only** — exact values for 0°, 30°, 45°, 60°, 90° are required by spec M5.18 and MM4.3. Non-standard angles are never used without an estimation context.
- **No ln()** — natural logarithm is NOT in the ESAT spec. log (base 10, exact powers only) may appear in Maths 2.
- **3 significant figures max** for numerical answers.

**Safe number pools for generation:**
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

The generation system prompt must include these conventions explicitly. The checker module (`verifiers/calculator_check.py`) validates every generated question against these rules. See `calculator-free-research.md` for the full ruleset, implementation pseudocode, and reference tables.

### 7.2 Computational Distractor Generation Pipeline

Generating plausible distractors is the single hardest part of ESAT question generation. Research (ReQUESTA framework) shows that AI-generated MCQs match human-authored questions on difficulty but significantly underperform on discrimination — the distractors are the gap.

#### Two-Stage Distractor Pipeline

**Stage 1: Computational Distractor Transforms**

For calculation questions (`generation_strategy: solution_first`), distractors are generated by applying specific error transforms to the correct solution path:

| Transform Type | Description | Example (circuit question) |
|---|---|---|
| **Formula swap** | Use a wrong but plausible formula | P = EMF × I instead of P = I² × R |
| **Unit confusion** | Correct value, wrong unit conversion | Answer in kJ when J was asked |
| **Sign error** | Direction/convention flipped | Negative velocity as positive |
| **Partial solution** | Stop one step short | Calculate force but not pressure |
| **Variable swap** | Use diameter instead of radius, sin instead of cos | mg sin θ → mg cos θ on incline |
| **Factor of 2** | Double or half via parallel/series confusion | R_ext = R1 + R2 for parallel circuit |
| **Forgotten term** | Omit internal resistance, friction, or air resistance | Exclude r from total resistance |

Each template specifies its own `distractor_generators` array (seen in the template schema). The orchestrator applies each transform computationally (via SymPy or direct arithmetic), producing numeric distractors that are guaranteed to be the result of a specific, identifiable error.

**Why computational, not LLM-generated?** When the LLM generates distractors freely, it tends to produce values that are either (a) obviously wrong (too far from the correct answer), (b) too close (ambiguous), or (c) not derivable from any plausible mistake. Computational transforms produce distractors that correspond to real student errors — exactly what Cambridge examiners craft.

**Stage 2: LLM-as-Judge Distractor Plausibility Filter**

After computational transforms produce 4 candidate distractors, a lightweight LLM check (Haiku 4.5, ~100 tokens) verifies:

1. **Plausibility:** Is each distractor a value a student might reasonably arrive at? (Reject absurd values)
2. **Uniqueness:** Are all 5 options (correct + 4 distractors) sufficiently distinct?
3. **No giveaway:** Do distractor lengths/formats not telegraph the correct answer? (Common LLM tell: correct answer is longest)

If any distractor fails the filter, it is regenerated from a different transform. If all transforms are exhausted, the LLM generates a replacement distractor under strict constraints.

#### Distractor Quality Metric

Each generated question's distractors are scored on:
- **Spread:** Standard deviation of option values (too tight = ambiguous, too wide = obvious)
- **Discrimination potential:** Do the distractors map to identifiable misconceptions?
- **Format consistency:** All options same format (all numeric, all algebraic, all statements)

These metrics feed into the Layer 5 quality rubric.

### 7.3 Self-Consistency for Complex Questions

For complex physics/math questions, use **self-consistency** (from academic literature on AQG):

1. Generate the question once
2. Have the solver model solve it **3 times independently** (different temperature/seed)
3. Take **majority vote** on the answer
4. If all 3 agree → high confidence → accept
5. If 2/3 agree → medium confidence → flag for review
6. If all disagree → reject and regenerate

### 7.4 Academic Literature Support

Research supports the multi-agent approach for AQG:

- **ReQUESTA framework** ([edtecharchives.org](https://edtecharchives.org/conference_proceeding/2551/25167)): Hybrid agentic framework combining LLM + rule-based agents for MCQ generation. Found that multi-agent approaches significantly improved question quality over single-model generation.

- **Multi-Agent Collaborative Framework for Math Problem Generation** ([EDM 2025](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.poster-demo-papers.288/index.html)): Proposes collaborative multi-agent system evaluated on relevance, importance, clarity, difficulty matching, and answerability.

- **Generating AI Literacy MCQs: Multi-Agent LLM Approach** ([arXiv:2412.00970](https://arxiv.org/html/2412.00970v1)): Expert evaluation showed strong interest in LLM-generated MCQs using multi-agent workflow.

- **SymPy for Neuro-Symbolic AI** ([TheDataGuy](https://thedataguy.pro/writing/2026/02/sympy-gen-ai-mathematical-reasoning)): Demonstrates that combining LLMs with SymPy eliminates mathematical hallucination — the LLM handles natural language while SymPy handles exact computation.

---

## 8. Recommendation

### Primary Recommendation: Architecture B (Premium Pipeline)

**Why Architecture B is the best choice for ESAT Gymnasium:**

1. **Cost is trivially low** — $38–$48 for 5,000 questions is negligible for a business. This is less than a single day of developer time.

2. **Quality is maximal** — Haiku 4.5 matches Sonnet 4 on coding benchmarks and is strong on STEM. Combined with Opus pattern extraction and multi-layer verification, quality will match or exceed human-written questions.

3. **Simplicity** — Single vendor (Anthropic), single API style, well-documented. No GPU management, no multi-vendor complexity.

4. **Batch API is perfect for this use case** — Question generation is not real-time. A 24-hour turnaround for 50% cost reduction is ideal.

5. **Proven models** — Claude models are the industry standard for high-quality content generation. The user already has access.

6. **TikZ diagram approach** — Code-based diagram generation is the academic standard, produces precise/consistent results, and costs essentially nothing beyond token generation.

7. **Scalable** — Can easily generate 10,000 or 50,000 questions at the same per-question cost.

### Implementation: Combine B + E

**The optimal real-world implementation combines Architecture B's pipeline with Architecture E's human-in-the-loop feedback:**

- Use Architecture B for the technical pipeline
- Add weekly human review of a 10–20% sample
- Feed insights back into the system prompt
- This costs ~$40 in API + ~2 hours/week of human time
- Quality continuously improves

### When to Consider Alternatives

| Scenario | Alternative |
|---|---|
| Budget is literally $0 | Architecture A (GLM free tier) |
| Want maximum possible quality, cost no object | Architecture C (mixed-model) |
| Generating 50,000+ questions or want independence from APIs | Architecture D (self-hosted Qwen 3) |
| Have subject-matter expert available for review | Architecture E (hybrid + human) |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1–2)

1. **Past Paper Digitization**
   - Download all ENGAA (2016–2023) and NSAA (2016–2023) past papers from [esat-tmua.ac.uk](https://esat-tmua.ac.uk/esat-preparation-materials)
   - Download ESAT specimen + practice tests
   - OCR/extract all questions into structured JSON format
   - Estimated: ~1,300 questions with answers

2. **Pattern Extraction (One-Time, 3-Stage Per-Topic Approach)**

   **Stage 1: Haiku Corpus Classification**
   - Every question in the past paper corpus (~2,500–3,000 questions) is classified by Haiku 4.5 (Batch API) into official ESAT Content Specification taxonomy codes (e.g. M2.11, B4.3, P3.5)
   - Each question receives: `spec_code`, `module`, `topic`, `subtopic`, `source`, `year`
   - All calls use Batch API (50% discount); Haiku is ideal for this classification work
   - Cost: ~$0.50–$1.00 total (~500 tokens input per question, ~50 tokens output)
   - Output: `data/classified/classified_corpus.json`

   **Stage 2: Opus Per-Topic Distractor & Pattern Extraction**
   - For EACH topic code in the ESAT spec that has questions in the classified corpus, run a dedicated Opus 4.8 Batch API call
   - Each call receives only the questions classified under that topic (typically 30–100 questions)
   - Opus extracts: distractor types, error patterns, misconception catalogues, common traps, difficulty calibration
   - Output per topic: `config/distractor_catalogue.<spec_code>.json`
   - ~36 calls across all modules (11 Maths 1+2 topics, 8 Physics, 8 Chemistry, 9 Biology)
   - Cost: ~$3.81 total (~$0.08–0.13 per call depending on topic size)

   **Stage 3: Opus Per-Topic Style Guide + Insight Scenarios**
   - For each topic, Opus also produces a topic-specific style guide and insight scenarios
   - Style guide: question structure patterns, difficulty calibration, wording conventions, calculator-free arithmetic patterns specific to this topic
   - Insight scenarios: 3–5 "Aha!" scenarios per topic requiring deep conceptual understanding
   - Output per topic: `config/style_guide.<spec_code>.md` and `config/insight_scenarios.<spec_code>.json`
   - Combined with Stage 2 into a single Opus call per topic (same input corpus, cached)
   - Combined Stage 2+3 cost per topic: ~$0.15–$0.20
   - Total combined Stage 2+3: ~$5.40–$7.20

   **Total one-time pattern extraction: ~$6–8** (see Section 10.2 for breakdown)
   - Key advantage: the official ESAT Content Specification IS the taxonomy and skill list — no need for Opus to derive these
   - Key advantage: per-topic Opus calls produce granular, focused output vs. broad module-level synthesis

3. **Template Library Creation**
   - Use Opus 4.8 to create 20–30 TikZ diagram templates per module
   - Templates parameterized (e.g., incline angle, resistance values, focal length)
   - Cost: ~$2–$5

4. **Template Library Creation**
   - Use Opus 4.8 to create 20–30 TikZ diagram templates per module
   - Templates parameterized (e.g., incline angle, resistance values, focal length)
   - Cost: ~$2–$5

5. **Insight Scenario Library Generation**
   - Generated as part of Stage 3 per-topic extraction calls (see Section 10.5.1)
   - 3–5 "Aha!" insight scenarios per topic across ~36 topics = 100–200 total scenarios with discrimination factors
   - Addresses the AI discrimination gap (0.32 vs 0.48 DI vs human-authored)
   - Cost: included in combined Stage 2+3 calls (~$5.40–$7.20 total)
   - Output: `config/insight_scenarios.<spec_code>.json` (per topic)

### Phase 2: Pipeline Development (Week 2–3)

4. **Build Python Pipeline**
   ```
   question_generator/
   ├── orchestrator.py      # Main pipeline coordinator
   ├── generators/
   │   ├── maths_gen.py     # Maths 1 & 2 generators
   │   ├── physics_gen.py   # Physics generator
   │   ├── chem_gen.py      # Chemistry generator
   │   └── bio_gen.py       # Biology generator
   ├── verifiers/
   │   ├── sympy_verify.py  # Symbolic math verification
   │   ├── solver_verify.py # LLM solver verification
   │   └── structural.py    # Format/distractor checks
   ├── diagrams/
   │   ├── tikz_compiler.py # LaTeX → PDF → SVG pipeline
   │   └── templates/       # Parameterized TikZ templates
   ├── reviewers/
   │   └── quality_score.py # Rubric-based quality scoring
   ├── output/
   │   └── export.py        # JSON output for web platform
   └── config/
       ├── style_guide.<spec_code>.md  # Per-topic style guides from Opus
       └── patterns.json    # Question patterns
   ```

5. **Set Up Anthropic Batch API**
   - Register for Batch API access
   - Build batching logic (collect questions, submit batch, retrieve results)
   - Implement prompt caching for shared system prompts

6. **Test with 100 Questions**
   - Generate 20 questions per module
   - Run through full pipeline
   - Human review all 100
   - Measure: quality score, rejection rate, cost per accepted question
   - Iterate on prompts based on results

### Phase 3: Production Generation (Week 4–12)

7. **Batch Generation Schedule**
   - Generate 500 questions/week (100/module)
   - Run automated verification
   - Human spot-check 20% (100 questions/week ~ 1 hour)
   - Export accepted questions to database
   - Timeline: 10 weeks for 5,000 questions

8. **Continuous Improvement**
   - Track rejection reasons
   - Update system prompts weekly
   - Expand template library
   - Build "gold standard" example set from best questions

### Phase 4: Scale & Optimize (Ongoing)

9. **Optional: Fine-tune for Cost Reduction**
   - Once 2,000+ verified questions exist, use them as training data
   - Fine-tune Haiku or a smaller model on the verified set
   - Or fine-tune self-hosted Qwen 3 for zero per-token cost

10. **Scale to "Infinite" Generation**
    - Target: 1,000+ new questions/month
    - Rotate syllabus topics to ensure coverage
    - Add difficulty calibration based on user performance data
    - Eventually offer user-requested topics

### Budget Summary

| Item | Cost |
|---|---|
| One-time: Pattern extraction — 3-stage per-topic approach (Stage 1: Haiku classification + Stage 2+3: Opus per-topic extraction) | $6–$8 |
| One-time: Template creation (Opus 4.8) | $5.00 |
| Phase 2: Test batch (100 questions) | $1.00 |
| Phase 3: 5,000 questions (Haiku Batch API) | $32–$36 |
| Infrastructure (LaTeX, hosting, etc.) | ~$5 |
| **Total project cost** | **~$49–$55** |

---

## Appendix A: Academic References

1. Su, H. et al. (2025). "Many Heads Are Better Than One: Improved Scientific Idea Generation by A LLM-Based Multi-Agent System." *ACL 2025.* [ora.ox.ac.uk](https://ora.ox.ac.uk/objects/uuid:d4d2a67a-d644-4cc8-850f-97cd3817cc79)

2. "Multi-Agent Collaborative Framework For Math Problem Generation." *EDM 2025.* [educationaldatamining.org](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.poster-demo-papers.288/index.html)

3. "Generating AI Literacy MCQs: A Multi-Agent LLM Approach." *SIGCSE TS 2025.* [arXiv:2412.00970](https://arxiv.org/html/2412.00970v1)

4. "Automatic Multiple-Choice Question Generation and Evaluation Using LLMs." *COLING 2025.* [aclanthology.org](https://aclanthology.org/2025.coling-main.154)

5. "ReQUESTA: A Hybrid Agentic Framework for Generating Cognitively Demanding MCQs." [edtecharchives.org](https://edtecharchives.org/conference_proceeding/2551/25167)

6. "SymPy: Bridging the Math Gap in Gen AI Systems." [TheDataGuy.pro](https://thedataguy.pro/writing/2026/02/sympy-gen-ai-mathematical-reasoning)

7. "LLM Agents for Education: Advances and Applications." *EMNLP 2025 Findings.* [aclanthology.org](https://aclanthology.org/2025.findings-emnlp.743.pdf)

## Appendix B: Pricing Sources

- **Anthropic:** [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing) (verified June 2026)
- **z.ai:** [docs.z.ai/guides/overview/pricing](https://docs.z.ai/guides/overview/pricing) (verified June 2026)
- **OpenAI:** [openai.com/api/pricing](https://openai.com/api/pricing) + [pricepertoken.com](https://pricepertoken.com/pricing-page/model/openai-gpt-4.1)
- **Gemini:** [cloud.google.com/vertex-ai/generative-ai/pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) + [costgoat.com](https://costgoat.com/pricing/gemini-api)
- **GPU Rental:** [vast.ai/pricing](https://vast.ai/pricing) + [getdeploying.com/gpus](https://getdeploying.com/gpus) + [blog.clore.ai](https://blog.clore.ai/gpu-cloud-pricing-comparison)
- **LLM Pricing Comparison:** [intuitionlabs.ai](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025) (comprehensive cross-provider analysis)
- **Anthropic Batch API:** [llmindset.co.uk](https://llmindset.co.uk/posts/2024/10/anthropic-batch-pricing) + [pristren.com](https://pristren.com/blog/anthropic-batch-api-guide)

---

---

## 10. Deep Dive: Pattern Extraction

The pattern extraction step converts the past paper corpus and the official ESAT Content Specification into actionable configuration files that drive question generation. The approach uses a **3-stage per-topic strategy**: Haiku 4.5 handles classification (its strength — simple tagging), and Claude Opus 4.8 handles deep reasoning (its strength — distractor analysis, style pattern extraction, and insight scenario generation). The official ESAT Content Specification PDF provides the taxonomy and skill list directly — no need for Opus to derive these from past papers.

### 10.1 Corpus: What We're Ingesting

**ENGAA (Engineering Admissions Assessment, 2016–2023):**
- 8 years × Section 1 (Maths + Physics, ~40 MCQs each) + Section 2 (Physics, ~20 MCQs)
- ~48 papers total (Section 1 + Section 2 per year)
- ~1,060 questions

**NSAA (Natural Sciences Admissions Assessment, 2016–2023):**
- 8 years × Section 1 (Maths + two science modules from Biology/Chemistry/Physics) + Section 2
- Note: NSAA 2016–2019 Section 2 had long-answer format (less relevant — not MCQ)
- For Section 1 only from 2020–2023 (all MCQ): ~24 papers × ~40 questions
- NSAA 2016–2019 Section 1: also MCQ format (~16 papers × ~40 questions)
- ~1,600 questions total (Section 1 + relevant Section 2)

**ESAT Specimen/Practice Tests (2024–2025):**
- 4 specimen papers (Maths 1, Physics, Chemistry, Biology, Maths 2)
- ~540 questions (5 modules × ~27 questions × 4 papers)

**Total estimated corpus: ~2,500–3,000 questions with solutions**

**Token estimate per question:**
- Question text: ~100–150 tokens
- 5 options (A–E): ~50–80 tokens
- Worked solution: ~150–250 tokens
- Metadata (year, paper, subject, section): ~30 tokens
- Average per question: ~350–500 tokens
- Total corpus: 3,000 × 400 = **~1.2M tokens**

This corpus does not need to fit in a single LLM context window. The 3-stage approach (Section 10.2) processes it efficiently: Haiku classifies individual questions, and Opus receives only the ~30–100 questions relevant to each topic code.


### 10.2 Three-Stage Per-Topic Extraction Strategy (Recommended)

**Architecture:** Instead of the old per-module 4-call system (which required Opus to derive the taxonomy and skill list from past papers), the new approach recognises that the **official ESAT Content Specification IS the taxonomy and skill list**. This eliminates the need for Opus to derive these from scratch. The remaining work — distractor pattern extraction, style guides, and insight scenario generation — is done per-topic using focused Opus calls, with Haiku handling the corpus classification step.

**Three stages:**

```
Stage 1: Haiku Classification
  Input:  Clean corpus (~2,500–3,000 questions) + ESAT spec taxonomy
  Model:  Claude Haiku 4.5 (Batch API, 50% discount)
  Output: classified_corpus.json — every question tagged with spec_code, module, topic, subtopic
  Cost:  ~$0.50–$1.00

Stage 2+3: Opus Per-Topic Extraction (combined into single calls per topic)
  Input:  Questions classified under one topic code + ESAT spec section for that topic
  Model:  Claude Opus 4.8 (Batch API, 50% discount)
  Output per topic:
    - distractor_catalogue.<spec_code>.json
    - style_guide.<spec_code>.md
    - insight_scenarios.<spec_code>.json
  Calls:  ~36 total (11 Maths 1+2 + 8 Physics + 8 Chemistry + 9 Biology)
  Cost:  ~$5.40–$7.20
```

**Total one-time cost: ~$6–$8** (down from $14.35, and higher quality due to per-topic focus).

**Key advantages over the old approach:**
1. **Official spec as ground truth** — the taxonomy and skill list come directly from the ESAT Content Specification, with no paraphrasing or gaps from Opus re-derivation
2. **Per-topic focus** — each Opus call sees only 30–100 questions for one specific topic, producing granular, immediately usable distractor patterns and style guides
3. **Lower cost** — Haiku handles classification (its strength), Opus handles deep reasoning (its strength), eliminating redundant taxonomy/skill derivation calls
4. **Parallelisable** — all ~36 per-topic calls are independent and can run as a single Batch API submission

#### 10.2.1 Stage 1: Haiku Per-Question Corpus Classification

Every question in the cleaned corpus is classified by Haiku 4.5 against the official ESAT Content Specification taxonomy. Haiku is ideal for this task — it's classification/tagging work where Opus would be wasteful.

**Batch setup:**
- All ~2,500–3,000 questions are submitted as a single Batch API job
- Each question gets ~500 tokens input (question text + options + spec topic list) and ~50 tokens output (spec_code + metadata)
- Haiku Batch pricing: $0.50/MTok input, $2.50/MTok output
- Cost: (2,750 × 500 × $0.50/MTok) + (2,750 × 50 × $2.50/MTok) = $0.69 + $0.34 = **~$1.00**

**Classification prompt structure:**
```
Given the following ESAT question and the official Content Specification topic codes
for the relevant module, classify this question to the most specific topic code.

Module: <Maths1|Maths2|Physics|Chemistry|Biology>
Available topic codes for this module: <from spec>

Question: <question text + options>

Output JSON: {"spec_code": "M1.3", "topic": "Algebra", "subtopic": "Quadratic equations", "confidence": 0.95}
```

**Output:** `data/classified/classified_corpus.json` — an array of classification records, grouped by spec_code. This grouped corpus becomes the input for each Stage 2+3 Opus call.

#### 10.2.2 Stage 2+3: Opus Per-Topic Extraction (Combined)

For each topic code in the ESAT spec that has classified questions in the corpus, a dedicated Opus 4.8 Batch API call extracts three artefacts:

1. **Distractor catalogue** — categorised distractor types with examples, misconception patterns, and generation strategies specific to this topic
2. **Style guide** — question structure patterns, difficulty calibration, wording conventions, and calculator-free arithmetic patterns for this topic
3. **Insight scenarios** — 3–5 "Aha!" scenarios that require deep conceptual understanding of this topic

**Why combine Stages 2 and 3:** The input for both stages is identical (the questions classified under this topic). Combining them into a single Opus call per topic avoids redundant input token costs and lets Opus produce more coherent, cross-referenced output.

**Topic distribution and estimated costs:**

| Module | Topic Codes | Questions per Topic (avg) | Cost per Topic (Batch Opus) | Total |
|---|---|---|---|---|
| **Maths 1 + Maths 2** | 11 (M1.1–M1.6, M2.1–M2.5) | ~70 | ~$0.17 | ~$1.87 |
| **Physics** | 8 (P1.1–P1.4, P2.1–P2.4) | ~85 | ~$0.19 | ~$1.52 |
| **Chemistry** | 8 (C1.1–C1.4, C2.1–C2.4) | ~60 | ~$0.15 | ~$1.20 |
| **Biology** | 9 (B1.1–B1.5, B2.1–B2.4) | ~45 | ~$0.13 | ~$1.17 |
| **Total** | **~36** | | | **~$5.76** |

*Cost ranges from ~$0.08 (small topics with ~30 questions, ~4K input tokens) to ~$0.20 (large topics with ~100 questions, ~15K input tokens). The estimates above are conservative.*

**Topics with no corpus coverage:** Some ESAT spec topics may have no questions in the past paper corpus (especially new or niche topics). These still get a style guide and insight scenarios generated, using only the ESAT spec text as input. Opus can generate plausible distractor patterns and question structures from the spec description alone, though with lower confidence. These outputs are flagged as `corpus_backed: false`.

#### 10.2.3 Opus Per-Topic Prompt Structure

Each per-topic Opus call receives:

```
<system prompt: see Section 10.4>

<ESAT Content Specification excerpt for topic {spec_code}>
  Topic: {topic_name}
  Subtopics: {list of subtopics from spec}
  Key concepts: {concept list from spec}

<Classified corpus questions for topic {spec_code}>
  Total questions: {N}
  Sources: ESAT ({n_esat}), NSAA ({n_nsaa}), ENGAA ({n_engaa})
  Years: {year_range}

Each question includes: question_text, options (A–E), correct_answer, worked_solution, source, year

<Source relevance weights: see Section 10.2.7>
```

Input tokens per topic are modest: typically 4K–15K (well within any context window). This means:
- No retrieval reliability concerns — Opus sees the full input with perfect attention
- Fast generation — smaller prompts produce output faster in Batch queue
- Focused output — Opus doesn't dilute reasoning budget across unrelated topics

#### 10.2.4 Cost-Saving Techniques Applied

| Technique | Where Applied | Savings |
|---|---|---|
| **Batch API** (50% discount) | All ~37 calls (1 Haiku classification + ~36 Opus per-topic) | Halves all token costs |
| **Small, focused inputs** | Opus per-topic calls | 4K–15K tokens per call (vs. 170K–350K in old approach) — dramatically lower per-call cost |
| **Haiku for classification** | Stage 1 | Haiku is ~28× cheaper than Opus per token for tagging work |
| **Official spec eliminates derivation** | Entire approach | No need for Opus to derive taxonomy or skills — those come from the ESAT PDF |

#### 10.2.5 Pricing Model

Haiku 4.5 pricing (Batch API, post-50% discount):
- Input: $0.50/MTok
- Output: $2.50/MTok

Opus 4.8 pricing (Batch API, post-50% discount):
- Input: $2.50/MTok
- Output: $12.50/MTok

**Stage 1 (Haiku classification) cost breakdown:**

| Item | Tokens | Rate | Cost |
|---|---|---|---|
| Input per question (question + options + spec topic list) | ~500 | $0.50/MTok | $0.00025 |
| Output per question (spec_code + metadata) | ~50 | $2.50/MTok | $0.000125 |
| Per question | — | — | $0.000375 |
| Total (2,750 questions) | — | — | **~$1.00** |

**Stage 2+3 (Opus per-topic) cost breakdown — Physics P1.1 as example (~85 questions):**

| Item | Tokens | Rate | Cost |
|---|---|---|---|
| Input (85 questions × ~200 tokens + spec excerpt + prompt) | ~18K | $2.50/MTok | $0.045 |
| Output (distractor catalogue + style guide + scenarios) | ~5K | $12.50/MTok | $0.0625 |
| **Total per topic** | — | — | **~$0.11** |

**All modules (Stage 2+3):**

| Module | Topic Codes | Total Cost |
|---|---|---|
| Maths 1 + Maths 2 | 11 | ~$1.87 |
| Physics | 8 | ~$1.52 |
| Chemistry | 8 | ~$1.20 |
| Biology | 9 | ~$1.17 |
| **Total Stage 2+3** | **~36** | **~$5.76** |

**Grand total: Stage 1 (~$1.00) + Stage 2+3 (~$5.76) = ~$6.76**

#### 10.2.6 Handling Mixed Corpus Sources

The per-topic approach naturally handles mixed corpus sources. Each question is already classified (Stage 1) and carries its `source` and `year` metadata. The Opus system prompt includes source relevance weights (see Section 10.2.7) so the model knows which sources to prioritise.

**Source relevance weighting** is determined by a separate research analysis (see `nsaa-engaa-esat-overlap-analysis.html` in the dashboard reports). The weighting informs how much Opus should trust each source when deriving patterns for a specific topic.

Topics that appear in the ESAT Content Specification but have no past paper coverage (spec-only topics) still get extraction calls — Opus uses only the spec text as input. These outputs are flagged as `corpus_backed: false`.

#### 10.2.7 Source Weighting in the Opus Prompt

Each per-topic Opus call includes source relevance weights so Opus knows which sources to trust when deriving patterns and templates for that specific topic. Weights are derived from the NSAA/ENGAA overlap analysis (see `nsaa-engaa-esat-overlap-analysis.html` in the dashboard reports).

A weight of 1.0 means the questions are essentially ESAT-equivalent. Lower weights indicate reduced reliability due to syllabus gaps, format differences, difficulty mismatches, or topic coverage issues.

Source weights are the same as in the old approach — see the tables below. The difference is that weights now apply per-topic rather than per-module, providing more granular control.

**Maths 1 + Maths 2 sources:**

| Source | Years | Weight | Notes |
|---|---|---|---|
| ESAT specimen/practice | 2024–2025 | **1.00** | Exact format, exact syllabus |
| NSAA S1 Part A (Maths) | 2016–2023 | **0.95** | Near-identical syllabus and format; gold-standard proxy |
| ENGAA S1 Part A (maths Qs only) | 2016–2023 | **0.85** | Same topics; **dedup vs NSAA required** |
| ENGAA S1 Part B (advanced maths Qs) | 2016–2023 | **0.85** | Strong topic overlap for Maths 2 |
| TMUA Paper 1 | 2017–2023 | **0.75** | Strong maths content; some topics not in ESAT — filter required |
| NSAA S2 (maths-heavy Qs) | 2020–2023 | **0.70** | Correct difficulty; some questions embedded in science contexts |

**Physics sources:**

| Source | Years | Weight | Notes |
|---|---|---|---|
| ESAT specimen/practice | 2024–2025 | **1.00** | Exact format, exact syllabus |
| NSAA S1 Part B (Physics) | 2016–2023 | **0.95** | Near-identical syllabus and format |
| ENGAA S1 Part A (physics Qs only) | 2016–2023 | **0.85** | Same topics; **dedup vs NSAA required** |
| NSAA S2 Physics (MCQ era) | 2020–2023 | **0.50** | **Advanced topics beyond ESAT spec — filter required.** ESAT Physics is GCSE/AS-level; NSAA S2 goes to A-level. Questions must be individually reviewed against the ESAT Physics spec before use. |

**Chemistry sources:**

| Source | Years | Weight | Notes |
|---|---|---|---|
| ESAT specimen/practice | 2024–2025 | **1.00** | Exact format, exact syllabus |
| NSAA S1 Part C (Chemistry) | 2016–2023 | **0.95** | Near-identical syllabus and format |
| NSAA S2 Part Y (Chemistry, MCQ era) | 2020–2023 | **0.50** | **Advanced topics beyond ESAT spec — filter required.** Off-syllabus questions must be excluded. |

**Biology sources:**

| Source | Years | Weight | Notes |
|---|---|---|---|
| ESAT specimen/practice | 2024–2025 | **1.00** | Exact format, exact syllabus |
| NSAA S1 Part D (Biology) | 2016–2023 | **0.95** | Near-identical syllabus and format |
| NSAA S2 Part Z (Biology, MCQ era) | 2020–2023 | **0.75** | Harder but generally within ESAT spec. More applied and data-heavy. |

#### 10.2.8 Critical Corpus Preparation Notes

Three issues must be addressed during corpus ingestion (Phase 1, Step 1) before the questions reach the extraction pipeline:

1. **ENGAA subject classification:** ENGAA Section 1 mixed maths and physics within each part. Questions must be classified by subject (maths vs physics) before use as proxy data for separate ESAT modules. This can be handled by Haiku during Stage 1 classification alongside the spec_code classification.

2. **NSAA/ENGAA deduplication:** Vantage Admissions and other expert sources confirm that "many [ENGAA] multiple-choice questions appear identically in the NSAA past papers." When building the proxy dataset from both NSAA and ENGAA, a deduplication step is essential. Dedup by question stem similarity (fuzzy match on normalised text). Without this, Opus would see the same question twice and double-count its frequency.

3. **NSAA S2 advanced topic filtering:** NSAA Section 2 questions (2020–2023 MCQ era) test A-level science topics that ESAT does not cover. ESAT Physics, Chemistry, and Biology are scoped to GCSE/AS-level content. NSAA S2 goes to full A-level depth. Every NSAA S2 question must be checked against the ESAT Content Specification and excluded if it tests a topic outside scope. The UAT-UK website has marked off-syllabus questions in their archived NSAA S2 papers — use their tagging as a reference. This applies primarily to:
   - **Physics S2:** capacitors, electromagnetic induction depth, thermal physics derivations, nuclear physics calculations beyond GCSE
   - **Chemistry S2:** transition metals, organic reaction mechanism depth, quantitative kinetics, buffer calculations
   - **Biology S2:** less affected, but some genetics and physiology questions go beyond ESAT scope

   **TMUA Paper 1** (useful for Maths 2) similarly contains topics not in ESAT (logic, proof, number theory) — filter questions against the ESAT Maths 2 spec before inclusion.

These three steps (subject classification, deduplication, spec filtering) are part of the corpus ingestion pipeline and must be completed before the Haiku classification and Opus extraction calls run.

### 10.3 What Qualitative Patterns Should Opus Extract? (Per-Topic)

The goal is to produce **per-topic style guides and distractor catalogues** that capture the DNA of Cambridge admissions questions for each ESAT Content Specification topic. For each topic code, Opus should extract:

#### 10.3.1 Question Structure Patterns

| Pattern Type | What to Extract | Example Insight |
|---|---|---|
| **Opening hook** | How questions frame the scenario | "A student observes..." / "In an experiment..." / "A block of mass m is placed on..." |
| **Information delivery** | How parameters are given | Explicit values, implied from diagrams, or embedded in text descriptions |
| **Multi-step structure** | How many reasoning steps to solution | Most ESAT questions require 3–5 sequential steps (e.g., calculate → substitute → simplify → evaluate) |
| **Answer format** | Numerical, algebraic, conceptual | Exact value, expression in variables, "which of the following is true" |
| **Option design** | How distractors are constructed | Common: off-by-one errors, sign errors, unit confusion, partial calculation results |

#### 10.3.2 Difficulty Calibration Patterns

| Difficulty Level | Token Characteristics | Typical ESAT Pattern |
|---|---|---|
| **Easy (1–3 on ESAT scale)** | Direct application of a single formula; minimal calculation; one concept | "What is the resistance of a wire..." given R = ρL/A directly |
| **Medium (4–6)** | 2–3 concepts combined; multi-step calculation; some algebraic manipulation | "A circuit with two resistors in parallel and one in series connected to a 12V battery..." |
| **Hard (7–9)** | Novel application; requires insight/trick; counterintuitive result; 4+ reasoning steps | "A satellite in elliptical orbit..." requiring conservation of energy + angular momentum insight |

Opus should output, for each difficulty level:
- Average number of reasoning steps
- Frequency of multi-concept synthesis vs. single-concept application
- Distribution of question types (calculation, conceptual, graphical interpretation, data analysis)

#### 10.3.3 Topic Distribution & Weightings

Opus should produce a frequency table of topics across all past papers:

```
Physics:
  Mechanics (kinematics, forces, energy):      35% of questions
  Electricity & circuits:                       20%
  Waves & optics:                               15%
  Thermal physics:                              10%
  Fields (gravitational, electric, magnetic):   10%
  Nuclear/radioactivity:                         5%
  Miscellaneous:                                 5%

Mathematics 1:
  Algebra & functions:                          25%
  Calculus (differentiation, integration):      20%
  Mechanics (SUVAT, projectiles):               15%
  Probability & statistics:                     15%
  Geometry & trigonometry:                      15%
  Number & proportion:                          10%
```

This becomes the **syllabus coverage target** for the generation system.

#### 10.3.4 Common Trap Distractors

Opus should catalogue the most common distractor strategies used by Cambridge:

| Trap Type | Description | Example |
|---|---|---|
| **Unit trap** | Correct numerical value but wrong units | Answer in kJ when question asks for J |
| **Sign error** | Forgetting direction/convention | Negative velocity reported as positive |
| **Partial solution** | Stops one step short | Calculates force but question asks for pressure |
| **Formula swap** | Uses wrong but plausible formula | Uses P=IV instead of P=I²R for power dissipation |
| **Diagram misread** | Misinterprets parallel vs. series, angle vs. complement | Reads angle from vertical instead of horizontal |
| **Calculator-free trap** | Creates calculation that's tedious without calculator | Forces simplification insight rather than brute computation |

#### 10.3.5 Cognitive Demand Classification

Map questions to Bloom's Taxonomy levels:
- **Remember** (recall facts, formulae): ~10% of ESAT
- **Apply** (use formulae in standard contexts): ~35%
- **Analyse** (break down problems, identify components): ~30%
- **Evaluate** (judge reasonableness, compare approaches): ~15%
- **Create** (novel synthesis, derive new relationships): ~10%

This distribution guides the generation system to produce questions at the right cognitive level.

### 10.4 Structuring the Opus Prompt for Per-Topic Pattern Extraction

#### Sample System Prompt

```
You are an expert assessment analyst specialising in Cambridge University
admissions tests (ENGAA, NSAA, ESAT). You have deep knowledge of A-Level
Mathematics, Physics, Chemistry, and Biology curricula, and you understand
the cognitive demands of high-stakes MCQ assessments.

You are analysing questions for ONE SPECIFIC TOPIC from the ESAT Content
Specification: {spec_code} — {topic_name}.

Your task is to analyse the corpus of past paper questions classified under
this topic and produce three outputs:
1. A distractor catalogue for this topic
2. A style guide for this topic
3. Insight scenarios ("Aha!" moments) for this topic

Output your analysis as structured JSON (for distractors and scenarios) and
Markdown (for the style guide). Be specific, quantitative, and evidence-based.
Quote example questions where helpful. Do not speculate — only report patterns
you can observe in the provided corpus.

Source weighting: ESAT questions (weight 1.0) are most authoritative. NSAA
(weight 0.95) and ENGAA (weight 0.85) are strong proxies. NSAA S2 (weight
0.50) and TMUA (weight 0.75) may include off-syllabus content — treat with
caution.
```

#### Sample User Prompt (abridged)

```
ESAT Content Specification — Topic {spec_code}: {topic_name}
Subtopics: {list from spec}
Key concepts and skills tested: {list from spec}

Below are {N} questions classified under this topic from ENGAA/NSAA past
papers (2016–2023) and ESAT specimen papers (2024–2025). Each question
includes question text, multiple-choice options (A–E), correct answer,
worked solution, source, and year.

Analyse this corpus and extract:

1. DISTRACTOR_CATALOGUE:
   - Categorise every distractor type observed in this topic's questions
     - distractor_type, frequency, example (quote the question), why_effective
   - For each distractor type, provide a generation strategy (how to
     produce similar distractors for new questions on this topic)
   - Common misconceptions and error patterns specific to this topic

2. STYLE_GUIDE:
   - Question structure patterns for this topic (opening hooks, information
     delivery, multi-step structure, answer format)
   - Difficulty calibration: what makes an easy vs hard question on THIS topic
   - Wording conventions specific to this topic
   - Calculator-free arithmetic patterns (what numbers appear, what
     simplifications are expected for this topic specifically)
   - "Trick" vs. "straightforward" question ratio for this topic

3. INSIGHT_SCENARIOS:
   - 3–5 "Aha!" scenarios for this topic
     - Each must involve 2–4 linked concepts from the ESAT spec for this topic
     - Each must contain a non-obvious insight rewarding deep understanding
     - Include: scenario description, the key insight, discrimination factors
       (specific misconceptions that produce wrong answers), difficulty_band

Output distractors and scenarios as valid JSON. Output style guide as Markdown.

[CORPUS BEGINS]
<questions classified under topic {spec_code}>
[CORPUS ENDS]
```

#### Sample Output: Style Guide Entry

```json
{
  "question_patterns": [
    {
      "pattern_name": "incline_with_friction_energy",
      "module": "Physics",
      "structure_description": "A block of mass m is placed on an incline at angle θ with coefficient of friction μ. Question asks for acceleration, final velocity, or work done against friction after travelling distance d.",
      "reasoning_steps": [
        "Resolve forces parallel and perpendicular to incline",
        "Apply F = ma along the incline (net force = mg sin θ - μ mg cos θ)",
        "Substitute given values",
        "Solve for target quantity (a, v, or W)"
      ],
      "typical_reasoning_steps": 4,
      "parameter_space": {
        "mass": "variable (symbolic or small numeric)",
        "angle": "30°, 37°, 45°, or symbolic θ",
        "friction_coefficient": "0.1–0.5 range",
        "distance": "symbolic d or 1–10 m"
      },
      "difficulty_band": "4-6",
      "common_distractors": [
        "Forgetting friction (using just mg sin θ)",
        "Using cos instead of sin for parallel component",
        "Normal force errors (using mg instead of mg cos θ)"
      ],
      "frequency": "appears in 8/48 Physics papers (17%)",
      "example_instantiation": "A block of mass 2.0 kg is placed on a plane inclined at 30° to the horizontal. The coefficient of friction between the block and the plane is 0.25. What is the acceleration of the block down the plane? (Take g = 9.8 m/s²)"
    }
  ]
}
```

### 10.5 Parameterized Question Templates

The most powerful output from Opus pattern extraction is **parameterized templates** — reusable question skeletons with variable slots that a cheaper model (Haiku, GLM) can instantiate infinitely.

**How it works:**

1. Opus analyses the corpus and identifies 50–100 recurring question patterns
2. For each pattern, Opus outputs a template with:
   - The question structure (text with `{{PARAMETERS}}`)
   - The solution pathway (step-by-step solution algorithm)
   - The parameter space (valid ranges, constraints)
   - Common distractor generators
3. At generation time, a cheap model (Haiku/GLM) receives the template + a random parameter draw and produces a fully instantiated question

**Concrete example template:**

```json
{
  "template_id": "PHYS_circuit_power_dissipation_01",
  "module": "Physics",
  "difficulty": "medium",
  "generation_strategy": "solution_first",
  "question_template": "A circuit consists of a battery of EMF {{EMF}} V with internal resistance {{r}} Ω connected to two resistors of resistance {{R1}} Ω and {{R2}} Ω arranged in {{arrangement}}. What is the total power dissipated in the external circuit?",
  "parameters": {
    "EMF": {"type": "numeric", "range": [6, 12], "decimal": 0},
    "r": {"type": "numeric", "range": [0.5, 3], "decimal": 1},
    "R1": {"type": "numeric", "range": [2, 20], "decimal": 0},
    "R2": {"type": "numeric", "range": [2, 20], "decimal": 0},
    "arrangement": {"type": "categorical", "values": ["series", "parallel"]}
  },
  "solution_algorithm": [
    "If series: R_ext = R1 + R2",
    "If parallel: R_ext = (R1 * R2) / (R1 + R2)",
    "Total resistance = R_ext + r",
    "Current I = EMF / (R_ext + r)",
    "Power = I² × R_ext"
  ],
  "answer_type": "numeric",
  "distractor_generators": [
    "Omit internal resistance: P_wrong = EMF² / R_ext",
    "Use P = EMF × I (total power, not external power)",
    "If parallel, use R_ext = R1 + R2 (treat as series)"
  ],
  "calculator_free_constraint": "Values chosen so answer is a clean fraction or simple decimal"
}
```

**Generation strategy field (`solution_first` vs `question_first`):**

Every template specifies a `generation_strategy` that controls how the LLM instantiates it:

- **`question_first`** (default): The LLM receives the template, fills in parameters, writes the question text, then derives the answer and worked solution. Used for conceptual, graphical, and interpretive questions.

- **`solution_first`**: The LLM first computes the answer using the `solution_algorithm` with specific parameter values, then writes the question text around that answer, and finally generates distractors from the `distractor_generators`. This guarantees clean, calculator-free numbers because the solution is derived symbolically before the question text is written. Used for all calculation-heavy templates (Physics mechanics, Maths calculus, Chemistry moles, circuit analysis, etc.).

**Why `solution_first` matters:** When the LLM writes the question first, it may choose parameter values that produce ugly intermediate calculations (e.g., a current of 2.73 A that then needs squaring). By computing the solution first with constrained parameters, we ensure every intermediate value is a clean fraction, integer, or simple decimal — consistent with ESAT's no-calculator rule.

**Which templates use `solution_first`:**
  - All Physics calculation templates (mechanics, circuits, energy, thermal, fields)
  - All Maths calculation templates (calculus, algebra, trigonometry)
  - Chemistry quantitative templates (moles, concentrations, bond energies, gas laws)
  - Any template where the answer is a numerical value derived from a formula

**Which templates use `question_first`:**
  - Conceptual/definition questions ("Which statement about X is correct?")
  - Graphical interpretation questions ("Which graph represents...")
  - Biology factual recall questions
  - Experimental method questions

### 10.5.1 Insight Scenario Library (Opus-Generated "Aha!" Templates — Per-Topic)

**The discrimination problem:** AI question generators produce procedurally solvable questions — apply the formula, get the answer. Real ESAT questions have an "Aha!" moment: a non-obvious insight, shortcut, or perspective shift that separates students who deeply understand the physics/maths from those who merely know the formulas. The ReQUESTA research confirms this is the single largest quality gap (AI discrimination index 0.32 vs human 0.48).

**Solution:** As part of Stage 3 of the per-topic extraction (Section 10.2.2), Opus generates 3–5 insight scenarios per topic code. Across ~36 topic codes, this produces 100–200 total scenarios — each one grounded in the specific topic's past paper corpus and the ESAT Content Specification for that topic.

**What an insight scenario looks like:**

```json
{
  "scenario_id": "INSIGHT_P1.1_bullet_in_block",
  "spec_code": "P1.1",
  "topic": "Forces and Motion",
  "aha_factor": "high",
  "scenario": "A bullet embeds in a wooden block resting on a rough surface. Find how far the block slides before stopping.",
  "insight": "Two-stage problem with a hidden link: (1) collision conserves momentum (not energy — inelastic), (2) resulting KE converts to work against friction. Students who try to do it in one step or who conserve energy during the collision get it wrong.",
  "discrimination_factors": [
    "Recognising inelastic collision (KE not conserved)",
    "Correctly linking collision result to sliding phase via velocity",
    "Not double-counting energy lost in collision vs energy lost to friction"
  ],
  "difficulty_band": "6-8",
  "template_hooks": ["incline_with_friction", "momentum_collision", "work_energy"]
}
```

**Example scenarios Opus should generate:**

| Scenario | Topic Code | Topics | Aha! Factor |
|---|---|---|---|
| Bullet embeds in block on rough surface | P1.1 | Momentum, energy, friction | Two-stage: collision is inelastic, then sliding dissipates KE |
| Satellite in elliptical orbit — compare speed at perigee/apogee | P2.3 | Energy conservation, angular momentum | Vis-viva equation shortcut; students who integrate get lost |
| Two resistors in parallel with internal resistance — find max power transfer | P1.4 | Circuits, calculus | Maximum power transfer theorem; derivative of P(R) |
| Symmetrical bridge circuit — find equivalent resistance | P1.4 | Circuits, symmetry | Symmetry allows cancellation without any calculation |
| Object floating in mercury, then oil added on top | P1.2 | Buoyancy, density | Two-fluid Archimedes; displaced volume changes |
| Projectile launched at angle θ from incline at angle α | M2.2 | Kinematics, vectors | Decompose along incline, not horizontal/vertical |
| Gas in sealed container with movable piston — heater turned on | C2.1 | Thermal, ideal gas | Isobaric vs isochoric confusion trap |
| Charged particle in crossed E and B fields — velocity selector | P2.4 | EM fields, circular motion | v = E/B condition; independent of mass and charge |
| Function with a removable discontinuity — find the limit | M1.4 | Calculus, limits | Factorise and cancel; students who substitute get infinity |
| Geometric series disguised as a recursive sequence | M1.2 | Algebra, series | Recognise the recurrence relation as geometric |

**How the scenario library integrates with generation:**

1. Each scenario links to one or more template IDs via `template_hooks` and is tagged with its `spec_code`
2. When the generator selects a template for a specific topic, it also selects an associated insight scenario from that topic's scenario file
3. The generation prompt includes both: "Use this template structure, but frame it within this scenario context"
4. The LLM produces a question that combines the template's mathematical structure with the scenario's insight factor
5. The discrimination factors are used by the QA rubric to verify the question actually requires the intended insight

**Cost:** Included in the Stage 2+3 per-topic Opus calls (~$5.40–$7.20 total). No separate scenario generation call is needed — Opus produces scenarios as part of the same call that generates the distractor catalogue and style guide for each topic.

**Where it lives:** `config/insight_scenarios.<spec_code>.json` (per topic) — loaded by the orchestrator when generating questions for that topic.

**Repos structure addition:**
```
  config/
  ├── insight_scenarios.P1.1.json    # Physics: Forces and Motion "Aha!" scenarios
  ├── insight_scenarios.P1.2.json    # Physics: Energy
  ├── ...                            # One file per topic code
  ```

**Cost of template-based generation:**
- Template instantiation requires only ~300 input tokens (template + parameter values) and ~200 output tokens
- Using GLM-4.5-Air: (300 × $0.20/M) + (200 × $1.10/M) = $0.00006 + $0.00022 = **$0.00028/question**
- This is **5× cheaper** than free-form generation because the model isn't designing the question — it's just filling in slots

**This approach is validated by academic research** — see the "Template-Based Generator for Single-Choice Questions" paper (PMC, 2023) which demonstrates that product-line engineering principles can generate question families with parameter variation from templates in learning management systems.

### 10.6 The ESAT Content Specification — Primary Taxonomy Source

The ESAT Content Specification (officially titled "Content Specification For assessment in October 2025 and January 2026") is published by UAT-UK as a PDF. It defines exactly what knowledge is tested. **In the new 3-stage approach, this spec IS the taxonomy and skill list** — no need for Opus to derive these from past papers.

**Ingestion and parsing strategy:**
1. **PDF → structured text:** Use `pdfplumber` or `PyMuPDF` (Python) to extract text, preserving section headings and bullet-point structure
2. **Parse into structured taxonomy JSON:** The spec (~15–20 pages, ~8K tokens) is parsed into a machine-readable JSON taxonomy with topic codes:

```json
{
  "module": "Physics",
  "spec_codes": [
    {
      "code": "P1.1",
      "topic": "Forces and Motion",
      "subtopics": [
        {"name": "Kinematics", "concepts": ["displacement", "velocity", "acceleration", "SUVAT"]},
        {"name": "Newton's Laws", "concepts": ["F=ma", "weight", "normal reaction", "friction"]},
        {"name": "Momentum", "concepts": ["conservation of momentum", "impulse"]}
      ]
    },
    {
      "code": "P1.2",
      "topic": "Energy",
      "subtopics": [
        {"name": "Work, energy, power", "concepts": ["W=Fd", "KE", "PE", "conservation"]},
        {"name": "Efficiency", "concepts": ["efficiency", "energy losses"]}
      ]
    },
    ...]
}
```

3. **This JSON becomes the input for Stage 1 classification** — Haiku maps each corpus question to the most specific `spec_code` from this taxonomy
4. **Each Opus per-topic call (Stage 2+3) receives the relevant topic excerpt** from this parsed spec, providing Opus with the exact syllabus boundaries for that topic
5. **Coverage validation:** The generation system can check-off topics as it generates questions, ensuring proportional representation across the full syllabus

**Key point:** The old approach had Opus derive the taxonomy (Call A) and skill list (Call B) from past papers — an expensive ($4–5) and error-prone process where Opus might paraphrase, miss, or restructure spec content. The new approach uses the official spec directly, ensuring 100% fidelity to the actual assessment specification.

### 10.7 Cost Summary for Pattern Extraction Step

| Approach | Calls | Est. Cost | Quality |
|---|---|---|---|
| Two-pass (legacy) | 2 | ~$4.50 | Good — broad but unfocused |
| Single-pass condensed | 1 | ~$4.75 | Good — risks attention dilution |
| Per-year thorough | 9 | ~$12.38 | Maximum — expensive |
| Per-module 4-call (old approach) | 17 | ~$14.35 | Excellent but wasteful — Opus derives taxonomy that the spec already provides |
| **3-Stage Per-Topic (recommended)** | **~37** | **~$6–$8** | **Best — official spec as taxonomy, per-topic Opus focus, granular output** |

**Recommendation:** 3-Stage Per-Topic approach with Batch API. Total one-time cost: **~$6–$8**.

**Why this is better than the old per-module approach:**
- **Cost:** ~$6–$8 vs ~$14.35 — less than half the price
- **Quality:** Per-topic Opus calls produce granular, focused distractor catalogues and style guides for every spec topic, rather than broad module-level outputs that mix topics
- **Accuracy:** The official ESAT Content Specification provides the taxonomy and skill list directly, with no risk of Opus paraphrasing or missing spec content
- **Efficiency:** Haiku handles classification (its strength), Opus handles deep reasoning (its strength) — no wasted frontier-model tokens on simple tagging tasks

---

## 11. Deep Dive: Diagram Generation by Subject

The first pass said "TikZ for everything." That's the right default, but Chemistry and Biology have specialised diagram needs that deserve their own treatment.

### 11.1 Chemistry Diagrams — Tool Assessment

#### 11.1.1 Molecular Structures (Lewis structures, ball-and-stick, skeletal)

| Tool | Capability | Programmatic? | Quality | Recommendation |
|---|---|---|---|---|
| **RDKit** (Python) | ⭐⭐⭐⭐⭐ | Yes — SMILES → 2D/3D structures | Publication quality | **Best choice** for any molecule |
| **chemfig** (LaTeX) | ⭐⭐⭐⭐ | Yes — LaTeX commands | Very good, academic style | Good for simple molecules, reaction schemes |
| **TikZ** (LaTeX) | ⭐⭐ | Possible but laborious | Mediocre for molecules | Not recommended for molecules |
| **MarvinSketch / ChemDraw** | ⭐⭐⭐⭐⭐ | No — GUI only | Professional | Not automatable |

**RDKit is the clear winner for molecular structures.** It's the industry-standard cheminformatics library:

```python
from rdkit import Chem
from rdkit.Chem import Draw, AllChem

# Generate a 2D molecular structure from SMILES
smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
mol = Chem.MolFromSmiles(smiles)
AllChem.Compute2DCoords(mol)

# Render to SVG (web-ready)
drawer = Draw.rdMolDraw2D.MolDraw2DSVG(400, 400)
drawer.DrawMolecule(mol)
drawer.FinishDrawing()
svg = drawer.GetDrawingText()

# Or render to PNG
img = Draw.MolToImage(mol, size=(400, 400))
img.save("aspirin.png")
```

**Why RDKit wins for ESAT:**
- LLM generates SMILES string → RDKit renders perfect structure diagram. SMILES is a well-documented notation that any STEM-capable LLM can produce reliably.
- Consistent output every time — no rendering variance
- Outputs SVG (web-native, crisp at any zoom)
- Handles stereochemistry, resonance structures, aromatic rings
- Can render reaction schemes: `Chem.Draw.ReactionToImage(rxn)`
- Installed via `pip install rdkit` — runs on the Oracle Cloud VM

**ESAT Chemistry use cases for RDKit:**
- Organic molecule structures (alkanes, alkenes, aromatics, functional groups)
- Reaction schemes (esterification, combustion, polymerisation)
- Isomer comparisons (structural vs. stereoisomers)
- Lewis structures (with custom atom/bond rendering)
- Molecular geometry (3D coordinates → 2D projection)

**What RDKit CAN'T do well:**
- Crystal lattices (use TikZ or custom SVG)
- Titration curves (use Matplotlib)
- Energy level / reaction coordinate diagrams (use TikZ/pgfplots)

#### 11.1.2 Reaction Mechanisms (curly arrows, electron movement)

| Tool | Recommendation |
|---|---|
| **chemfig + \chemmove** | Best — LaTeX package designed for exactly this. Can draw curly arrows between atoms in a chemfig structure |
| **RDKit** | Not designed for mechanism arrows |
| **TikZ overlays on RDKit SVG** | Possible but fiddly |

**chemfig example for a reaction mechanism:**
```latex
\schemestart
  \chemfig{H_3C-C(=[::0]O)-[::-60]OH}
  \arrow{->[\chemfig{H^{\oplus}}]}
  \chemfig{H_3C(=[::0]\charge{90=\:}{O}^{-::-60]OH})}
\schemestop
```

For ESAT, mechanisms are rarely required in MCQ format — the question usually describes the mechanism textually. Where mechanism diagrams appear, a small library of 5–10 pre-drawn templates (esterification, nucleophilic substitution, electrophilic addition) parameterised by the specific molecules covers ~95% of cases.

#### 11.1.3 Energy Level Diagrams / Reaction Coordinates

| Tool | Recommendation |
|---|---|
| **TikZ + pgfplots** | ⭐⭐⭐⭐⭐ — Excellent. TeX.SE has many proven templates for reaction coordinate diagrams |
| **Matplotlib** | ⭐⭐⭐⭐ — Good for quick generation, less precise styling |

**TikZ/pgfplots example for energy diagram:**
```latex
\begin{tikzpicture}
  \begin{axis}[
    xlabel={Reaction progress},
    ylabel={Energy},
    xtick=\empty, ytick=\empty,
    axis lines=left,
    width=8cm, height=6cm,
  ]
    \addplot[smooth, thick, blue] coordinates {
      (0, 2) (1, 5) (2, 1) (3, 4) (4, 0.5)
    };
    \node at (axis cs:1, 5.5) {Activation energy};
    \node at (axis cs:0, 2.5) {Reactants};
    \node at (axis cs:4, 1) {Products};
    \draw[<->, red] (axis cs:0, 2) -- (axis cs:0, 5);
    \draw[<->, red] (axis cs:0, 2) -- (axis cs:4, 0.5);
  \end{axis}
\end{tikzpicture}
```

This template can be parameterised: change the energy levels and labels, and the diagram adapts automatically. Perfect for exothermic/endothermic reactions, catalysis effects, multi-step reactions.

#### 11.1.4 Titration Curves

Best tool: **Matplotlib** (not TikZ/pgfplots — Matplotlib's curve fitting is more natural for pH titration data).

```python
import matplotlib.pyplot as plt
import numpy as np

# Titration curve: strong acid + strong base
vol_added = np.linspace(0, 50, 1000)
# Simple titration calculation
pH = np.where(vol_added < 25,
    -np.log10(0.1 * 25 / (25 + vol_added)),  # Pre-equivalence
    14 + np.log10(0.1 * (vol_added - 25) / (25 + vol_added)))  # Post-equivalence
plt.plot(vol_added, pH, 'b-', linewidth=2)
plt.xlabel('Volume of NaOH added (mL)')
plt.ylabel('pH')
plt.title('Titration: HCl + NaOH')
plt.savefig('titration.svg', format='svg')
```

The LLM generates the Python code with the correct parameters → Matplotlib renders an accurate titration curve.

#### 11.1.5 Crystal Lattices

| Tool | Recommendation |
|---|---|
| **TikZ** (3D lattice) | Good — can draw cubic, FCC, BCC lattices with 3D coordinates |
| **Custom SVG templates** | Good — pre-drawn lattice structures parameterised by atom spacing |
| **3Dmol.js** (JavaScript) | Excellent for web — interactive 3D, but overkill for MCQ |

For ESAT, a small library of 5 template lattices (simple cubic, BCC, FCC, ionic NaCl-type, diamond) parameterised by edge length covers all likely question types.

### 11.2 Biology Diagrams — Tool Assessment

Biology is the **hardest subject for code-generated diagrams** because many diagrams are illustrative (cell cross-sections, organelles, biological specimens) rather than schematic.

#### 11.2.1 What's Code-Generatable in Biology?

| Diagram Type | Tool | Code-Generatable? | Quality |
|---|---|---|---|
| **Pedigree charts** | TikZ | ✅ Yes — fully | ⭐⭐⭐⭐⭐ |
| **Ecological pyramids** | TikZ / Matplotlib | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **Energy flow diagrams** | TikZ | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **Food webs** | TikZ | ✅ Yes — graph layout | ⭐⭐⭐⭐ |
| **Punnett squares** | LaTeX tables | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **Genetics crosses** | TikZ + tables | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **Graphs (enzyme kinetics, population)** | Matplotlib | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **DNA/mRNA diagrams** | TikZ | ⚠️ Partially — schematic, not realistic | ⭐⭐⭐ |
| **Enzyme-substrate models** | TikZ (lock-and-key) | ⚠️ Schematic only | ⭐⭐⭐ |
| **Cell structure cross-sections** | TikZ | ⚠️ Basic shapes only | ⭐⭐ |
| **Organelle illustrations** | TikZ | ⚠️ Very basic | ⭐⭐ |
| **Experimental setups** | TikZ | ✅ Yes — apparatus diagrams | ⭐⭐⭐⭐ |

#### 11.2.2 The Cell Diagram Problem

Cell structure cross-sections and organelle illustrations are the **biggest gap** — TikZ can draw basic geometric shapes (ellipses, rounded rectangles) but cannot produce the kind of detailed, labelled biological illustrations seen in Cambridge exams.

**Approaches for illustrative biology diagrams:**

**Approach A: Template library (recommended)**
- Pre-draw 20–30 biology diagram templates in a vector editor (Inkscape/Illustrator)
- Store as parameterised SVG files
- The LLM selects the appropriate template and fills in labels/parameters
- Templates: animal cell, plant cell, neuron, leaf cross-section, root cross-section, DNA double helix, enzyme-substrate complex, membrane structure
- Pro: Consistent, high quality, web-ready
- Con: Requires initial manual creation effort

**Approach B: BioRender-style icon library**
- Use [bioicons.com](https://bioicons.com) (free, open-source SVG icons for biology)
- Combine icons programmatically using SVG manipulation (Python `svglib` or direct SVG templating)
- Less artistic control but faster than hand-drawing

**Approach C: SciDraw AI / FigCanvas**
- AI-assisted scientific illustration tools that generate figures from text descriptions
- SciDraw AI: generates BioRender-style figures from prompts
- Useful for one-off complex illustrations
- Not suitable for automated batch generation (cost, variability)

**Approach D: LLM generates TikZ schematic**
- Accept that biology diagrams will be more schematic than illustrative
- TikZ can draw "good enough" cell diagrams using labeled ellipses and circles for organelles
- Quality is lower than hand-drawn but acceptable for many MCQ contexts
- Many ESAT biology questions reference diagrams that are primarily about *interpreting data* (graphs, charts) rather than *identifying structures*

**Recommendation for Biology:** Use a **hybrid approach**:
1. Code-generated (TikZ/Matplotlib) for: pedigree charts, ecological pyramids, energy flow, genetics crosses, enzyme kinetics graphs, population graphs, experimental data
2. Template library (pre-drawn SVGs) for: cell structure, organelles, DNA diagrams, membrane structure
3. This covers ~90% of ESAT Biology diagram needs. The remaining ~10% can be hand-drawn as needed

### 11.3 Diagram Generation Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                 DIAGRAM GENERATION PIPELINE                  │
│                                                             │
│  Question context → LLM classifies diagram type              │
│                          │                                  │
│          ┌───────────────┼───────────────┐                  │
│          ▼               ▼               ▼                  │
│    [SCHEMATIC]     [MOLECULAR]    [ILLUSTRATIVE]            │
│    TikZ/Matplotlib   RDKit (SMILES)   Template Library      │
│    pgfplots          chemfig          (pre-drawn SVGs)       │
│          │               │               │                  │
│          ▼               ▼               ▼                  │
│    LaTeX compile    Python render    SVG parameter fill     │
│    → PDF → SVG      → SVG/PNG        → final SVG            │
│          │               │               │                  │
│          └───────────────┼───────────────┘                  │
│                          ▼                                  │
│                   [SVG output for web]                       │
│                          │                                  │
│                          ▼                                  │
│              Vision model verification                       │
│              (GLM-4.6V-Flash — FREE)                        │
│              "Does this diagram match the question?"        │
└─────────────────────────────────────────────────────────────┘
```

### 11.4 Diagram Cost Breakdown

| Diagram Type | Generation Cost | Render Cost | Total |
|---|---|---|---|
| Physics (TikZ, LaTeX) | $0.0035 (Haiku) | Free (pdflatex) | $0.0035 |
| Chemistry molecule (RDKit) | $0.0010 (SMILES gen only) | Free (RDKit) | $0.0010 |
| Chemistry graph (pgfplots) | $0.0035 (Haiku) | Free (pdflatex) | $0.0035 |
| Biology schematic (TikZ) | $0.0035 (Haiku) | Free (pdflatex) | $0.0035 |
| Biology template (pre-drawn) | $0.0005 (template select) | Free (SVG fill) | $0.0005 |
| **Average (weighted)** | | | **~$0.0025** |

---

## 12. OpenClaw as Orchestration Layer

The user already has OpenClaw running on their Oracle Cloud VM with GLM access. This is essentially free infrastructure that can serve as the question generation orchestration layer.

### 12.1 What OpenClaw Provides

OpenClaw is an always-on AI agent gateway that runs on user infrastructure. Key capabilities relevant to question generation:

| Capability | How It Helps |
|---|---|
| **Multi-model routing** | Can call GLM, Claude, OpenAI, Gemini models from a single agent — no multi-vendor SDK code |
| **Cron jobs** | Schedule batch generation jobs (e.g., "generate 50 Physics questions every night at 2 AM") |
| **Skill files** | Define reusable question-generation skills (templates, verification rubrics) |
| **Session management** | Each generation batch runs in an isolated session — no context bleed |
| **Heartbeat system** | Monitor generation queue, check for stalled batches, trigger retries |
| **Subagent spawning** | Spawn specialised sub-agents for each module (Physics agent, Chemistry agent, etc.) |
| **Workspace files** | Store style guides, templates, and generated questions in the agent workspace |
| **Channel delivery** | Questions can be delivered to Telegram, web, or any connected channel |

### 12.2 Architecture: OpenClaw-Managed Question Generation

```
┌────────────────────────────────────────────────────────────────────┐
│                    OPENCLAW GATEWAY (Oracle Cloud VM)               │
│                                                                    │
│  ┌──────────────────────────────────────────────────────┐          │
│  │  CRON JOB: "Nightly Question Generation"              │          │
│  │  Runs at 2:00 AM daily                                │          │
│  │  → Triggers question generation pipeline               │          │
│  └────────────────────────┬─────────────────────────────┘          │
│                           │                                        │
│  ┌────────────────────────▼─────────────────────────────┐          │
│  │  GENERATION AGENT (OpenClaw skill)                     │          │
│  │  Reads: style_guide.<topic>.md, distractor_catalogue.<topic>.json, question_templates.json        │          │
│  │  Uses: GLM-5 or Haiku 4.5 for question generation      │          │
│  │  Uses: SymPy (local Python) for math verification      │          │
│  │  Uses: RDKit (local Python) for molecule rendering     │          │
│  │  Uses: pdflatex (local) for TikZ → SVG                 │          │
│  └────────────────────────┬─────────────────────────────┘          │
│                           │                                        │
│  ┌────────────────────────▼─────────────────────────────┐          │
│  │  VERIFICATION AGENT (subagent)                         │          │
│  │  Uses: different model than generator                  │          │
│  │  Runs: SymPy check, structural checks, rubric scoring  │          │
│  │  Output: JSON with pass/fail + quality score           │          │
│  └────────────────────────┬─────────────────────────────┘          │
│                           │                                        │
│  ┌────────────────────────▼─────────────────────────────┐          │
│  │  OUTPUT: questions.json → Database (SQLite/Postgres)   │          │
│  │  → Web platform reads from database                    │          │
│  └──────────────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────────────┘
```

### 12.3 OpenClaw vs. Standalone Python Script

| Factor | OpenClaw-Managed | Standalone Python Script |
|---|---|---|
| **Setup complexity** | Low — configure cron job + skill file | Medium — write full pipeline + scheduler |
| **Multi-model access** | Built-in — just change model name in config | High — implement API clients for each provider |
| **Scheduling** | `openclaw cron add` — one command | Need crontab, systemd timer, or Airflow |
| **Monitoring** | Heartbeat checks, session history, Telegram alerts | Must build custom logging + alerting |
| **Retries** | Built-in session management | Must implement retry logic |
| **Flexibility** | Constrained to OpenClaw paradigms | Full control over every aspect |
| **Speed** | Overhead from agent loop (seconds per question) | Direct API calls (milliseconds) |
| **Cost** | Free (already running) | Free |
| **GLM integration** | Native — already configured | Need GLM API client |
| **Debugging** | OpenClaw session logs, message history | Standard Python debugging |

**Recommendation: Hybrid approach**

Use OpenClaw for **orchestration and scheduling** but run the actual generation as a Python script triggered by OpenClaw's cron system:

1. OpenClaw cron job triggers at 2 AM
2. Cron job message tells the agent to run: `python3 /path/to/generate_questions.py --batch 50 --module physics`
3. Python script does the heavy lifting (API calls, SymPy, RDKit, LaTeX compilation)
4. Python script outputs questions to JSON file
5. Agent verifies output, sends summary to Telegram

This gives you the best of both worlds: OpenClaw's scheduling/monitoring/notifications + Python's speed and flexibility for the generation pipeline.

### 12.4 Concrete OpenClaw Setup

**Cron job creation:**
```bash
openclaw cron add \
  --schedule "0 2 * * *" \
  --name "Nightly Question Generation" \
  --message "Run the ESAT question generation pipeline. Execute: python3 /home/ubuntu/esat-gymnasium/generate.py --batch 50 --module physics. After completion, verify output quality and send a summary to Telegram with: total generated, passed verification, rejected, topics covered." \
  --agent esat-manager \
  --session isolated
```

**Skill file** (`~/.openclaw/workspace/esat-manager/skills/esat-generation/SKILL.md`):
```markdown
# ESAT Question Generation Skill

## Trigger
When asked to generate ESAT questions or when the nightly cron fires.

## Procedure
1. Run the Python generation pipeline
2. Check output JSON for completeness
3. Verify all questions have: text, 5 options, correct answer, worked solution
4. Count by difficulty and topic
5. Report summary

## Quality Standards
- Every question must pass SymPy verification (where applicable)
- Every diagram must compile
- No duplicate questions (embedding similarity < 0.85)
```

### 12.5 GLM Integration via OpenClaw

The user's OpenClaw instance already has GLM configured (z.ai models). This means:
- GLM-4.5-Air ($0.20/$1.10 per MTok) or GLM-5 ($1.00/$3.20) can be called from any OpenClaw agent
- The free tier models (GLM-4.7-Flash, GLM-4.5-Flash) are available for zero-cost generation
- OpenClaw handles authentication, rate limiting, retries automatically
- No additional API client code needed

This makes the **Budget Pipeline (Architecture A)** essentially free to operate — the user's existing OpenClaw + GLM setup covers generation, and local Python handles verification.

---

## 13. Infinite Generation: Deduplication & Coverage

The platform promises "infinitely generated questions." At scale, two problems emerge:
1. **Near-duplicate proliferation** — the same question rephrased slightly differently
2. **Coverage gaps** — some topics over-represented, others neglected

### 13.1 Embedding-Based Deduplication

**How it works:**

Every generated question is converted to a dense vector embedding (a mathematical representation of its semantic meaning). New questions are compared against the existing bank; if a new question's embedding is too similar to an existing one, it's rejected.

**Implementation:**

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import json

# Load embedding model (384-dimensional, fast, runs on CPU)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialise or load FAISS index
dimension = 384
index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity after normalisation)

# Load existing question embeddings (if any)
existing_questions = load_questions_from_db()
if existing_questions:
    embeddings = model.encode([q['text'] for q in existing_questions])
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

# Deduplication check for a new question
def is_duplicate(question_text, threshold=0.85):
    """Returns True if the question is too similar to an existing one."""
    embedding = model.encode([question_text])
    faiss.normalize_L2(embedding)
    
    # Search for nearest neighbours
    scores, indices = index.search(embedding, k=5)
    
    if scores[0][0] > threshold:
        return True, indices[0][0], scores[0][0]
    return False, None, scores[0][0]

# Pipeline integration
def process_new_question(question):
    is_dup, similar_idx, similarity = is_duplicate(question['text'])
    if is_dup:
        return {'status': 'rejected', 'reason': 'duplicate',
                'similar_to': similar_idx, 'similarity': similarity}
    
    # Add to index
    embedding = model.encode([question['text']])
    faiss.normalize_L2(embedding)
    index.add(embedding)
    
    # Store in database
    save_to_db(question)
    return {'status': 'accepted'}
```

**Threshold selection:**
- **0.95+**: Near-exact duplicates only (very permissive — allows very similar questions)
- **0.85–0.90**: Catches structural duplicates with different numbers/scenarios (recommended)
- **0.75–0.80**: Catches conceptually similar questions (may be too aggressive)
- **Recommendation: 0.85** for ESAT — allows questions on the same topic with different approaches, but catches questions that are essentially the same with different numbers

**Embedding model options:**

| Model | Dimensions | Speed | Quality | Size |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | Very fast (CPU) | Good | 80 MB |
| `all-mpnet-base-v2` | 768 | Fast | Better | 420 MB |
| `bge-small-en-v1.5` | 384 | Very fast | Good | 130 MB |
| `bge-large-en-v1.5` | 1024 | Moderate | Best | 1.3 GB |

**Recommendation:** `all-MiniLM-L6-v2` for speed; `bge-large-en-v1.5` for maximum quality. Both run on CPU — no GPU needed.

**FAISS performance:**
- IndexFlatIP with 100K questions: <1ms per query on CPU
- IndexIVFFlat (approximate): <0.1ms per query for 1M+ questions
- The deduplication check adds negligible time to the generation pipeline

**Cost:** $0 — runs entirely locally on the Oracle Cloud VM. No API calls.

### 13.2 Syllabus Coverage Tracking

The system must ensure proportional representation of all ESAT topics over time.

**Implementation:**

```python
# Syllabus coverage matrix (extracted from Opus pattern analysis)
COVERAGE_TARGETS = {
    "Physics": {
        "Mechanics": {"target_pct": 35, "subtopics": {
            "kinematics": 10, "forces": 10, "energy": 8, "momentum": 7
        }},
        "Electricity": {"target_pct": 20, "subtopics": {
            "circuits": 12, "fields": 5, "electromagnetism": 3
        }},
        "Waves": {"target_pct": 15, "subtopics": {
            "wave_properties": 8, "optics": 4, "sound": 3
        }},
        "Thermal": {"target_pct": 10, "subtopics": {
            "heat_transfer": 5, "gas_laws": 5
        }},
        "Fields": {"target_pct": 10, "subtopics": {
            "gravitational": 5, "electric": 5
        }},
        "Nuclear": {"target_pct": 5, "subtopics": {
            "radioactivity": 3, "nuclear_physics": 2
        }},
        "Misc": {"target_pct": 5, "subtopics": {}}
    },
    # ... similar for Maths1, Maths2, Chemistry, Biology
}

class CoverageTracker:
    def __init__(self):
        self.generated = {}  # {module: {topic: count}}
        self.load_from_db()
    
    def get_underrepresented_topic(self, module):
        """Returns the topic most in need of questions."""
        total = sum(self.generated.get(module, {}).values()) or 1
        deficits = []
        for topic, target in COVERAGE_TARGETS[module].items():
            current_pct = self.generated.get(module, {}).get(topic, 0) / total * 100
            deficit = target['target_pct'] - current_pct
            deficits.append((topic, deficit))
        deficits.sort(key=lambda x: -x[1])
        return deficits[0][0]  # Topic with largest deficit
    
    def get_generation_directive(self, module, batch_size=50):
        """Returns a directive for the generator: what topics to cover."""
        directive = {"module": module, "questions": []}
        for _ in range(batch_size):
            topic = self.get_underrepresented_topic(module)
            directive["questions"].append({"topic": topic, "difficulty": self.get_difficulty_target()})
        return directive
```

### 13.3 Difficulty Calibration Over Time

**Maintaining the 20/50/30 easy/medium/hard split:**

```python
class DifficultyBalancer:
    def __init__(self):
        self.target = {"easy": 0.20, "medium": 0.50, "hard": 0.30}
        self.actual = self.load_actual_distribution()
    
    def get_difficulty_target(self):
        """Returns which difficulty the next question should target."""
        total = sum(self.actual.values()) or 1
        deficits = {
            d: self.target[d] - self.actual.get(d, 0) / total
            for d in self.target
        }
        # Pick the difficulty with the largest deficit
        return max(deficits, key=deficits.get)
```

**Dynamic calibration based on user performance:**
If the platform tracks user answer rates, the system can dynamically adjust difficulty:
- If >80% of users answer a question correctly → recalibrate it as "easy"
- If <20% answer correctly → recalibrate as "hard"
- This creates a feedback loop that improves difficulty targeting over time
- Requires storing per-question user performance data

### 13.4 Generating Infinite Variations from Finite Patterns

The question is: how do you generate infinite questions from a finite set of patterns without repetition?

**Three mechanisms:**

1. **Parameter explosion:** A single template with 5 parameters, each with 10 possible values, produces 10⁵ = 100,000 unique instantiations. With 50–100 templates across all modules, the parameter space is effectively infinite for practical purposes.

2. **Compositional variation:** Combine two patterns into one question (e.g., a circuit question that also requires a kinematics calculation). This multiplies the pattern space.

3. **Contextual reframing:** The same physics concept (e.g., conservation of energy) can be framed as: a roller coaster, a pendulum, a spring, a satellite orbit, a block on a ramp, a collision. Each framing produces a different question testing the same concept.

**Practical limit:** With 100 templates × 5 parameters × 10 values each × 5 contextual framings = 5,000,000 unique question structures. The system will never run out.

The real constraint is not uniqueness but **quality maintenance** — ensuring that parameter combinations produce solvable, unambiguous questions. This is why SymPy verification and solver verification are essential even for template-based generation.

---

## 14. Concrete Implementation Architecture

This section synthesises all findings into a specific, practical architecture using the user's actual resources.

### 14.1 Available Resources

| Resource | Status | Cost |
|---|---|---|
| Oracle Cloud VM (ARM, 4 OCPU, 24GB RAM) | Running | Free tier |
| OpenClaw with GLM access | Running | GLM API costs |
| Claude API access | Available | Pay per token |
| OpenAI API access | Available | Pay per token |
| Gemini free tier | Available | Free (rate-limited) |
| Python 3.x, SymPy, RDKit | Installable | Free |
| LaTeX (TeX Live, pdflatex) | Installable | Free |
| FAISS, sentence-transformers | Installable | Free |
| SQLite/Postgres | Installable | Free |

### 14.2 Recommended Stack

```
┌─────────────────────────────────────────────────────────────┐
│                   ESAT GYMNASIUM STACK                       │
│                                                             │
│  ORCHESTRATION LAYER                                        │
│  ├── OpenClaw (cron scheduling, monitoring, Telegram alerts)│
│  └── Python pipeline (async, direct API calls)              │
│                                                             │
│  GENERATION LAYER                                           │
│  ├── Primary: Claude Haiku 4.5 (Batch API, 50% off)        │
│  ├── Budget: GLM-4.5-Air ($0.20/$1.10 per MTok)            │
│  ├── Free: GLM-4.5-Flash (rate-limited, $0)                │
│  └── One-time: Claude Opus 4.8 (pattern extraction)        │
│                                                             │
│  VERIFICATION LAYER                                         │
│  ├── SymPy (local Python, $0) — math verification          │
│  ├── Haiku 4.5 solver (Batch API) — LLM verification       │
│  ├── Structural checks (Python, $0) — format validation    │
│  └── GLM-4.6V-Flash (FREE) — diagram vision check          │
│                                                             │
│  DIAGRAM LAYER                                              │
│  ├── Physics: TikZ → pdflatex → PDF → SVG                  │
│  ├── Chemistry molecules: RDKit (SMILES → SVG)             │
│  ├── Chemistry graphs: pgfplots / Matplotlib → SVG         │
│  ├── Biology schematic: TikZ → SVG                         │
│  └── Biology illustrative: Pre-drawn SVG template library  │
│                                                             │
│  QUALITY LAYER                                              │
│  ├── FAISS + sentence-transformers — deduplication          │
│  ├── Coverage tracker — syllabus coverage matrix            │
│  ├── Difficulty balancer — 20/50/30 distribution            │
│  └── Quality rubric (Haiku 4.5 Batch API) — scoring        │
│                                                             │
│  STORAGE LAYER                                              │
│  ├── SQLite/Postgres — question bank                        │
│  ├── Filesystem — FAISS index, templates, style guide       │
│  └── JSON export → Web platform                             │
│                                                             │
│  INFRASTRUCTURE                                             │
│  ├── Oracle Cloud VM (ARM) — runs everything                │
│  ├── OpenClaw — scheduling, monitoring, alerts              │
│  └── Web platform — consumes question bank JSON             │
└─────────────────────────────────────────────────────────────┘
```

### 14.3 Repository Structure

```
/home/ubuntu/esat-gymnasium/
├── README.md
├── config/
│   ├── spec_taxonomy.json      # ESAT Content Specification parsed into topic codes
│   ├── style_guide.<spec_code>.md    # Per-topic style guides (Opus, one per topic)
│   ├── distractor_catalogue.<spec_code>.json  # Per-topic distractor patterns (Opus)
│   ├── insight_scenarios.<spec_code>.json     # Per-topic "Aha!" scenarios (Opus)
│   ├── question_patterns.json   # Opus-extracted pattern templates
│   └── coverage_targets.json    # Syllabus weightings (derived from spec + classified corpus)
│   └── models.json               # Model configuration per pipeline stage
├── src/
│   ├── orchestrator.py           # Main pipeline coordinator
│   ├── generators/
│   │   ├── maths1_gen.py         # Maths 1 question generation
│   │   ├── maths2_gen.py         # Maths 2 generation
│   │   ├── physics_gen.py        # Physics generation
│   │   ├── chem_gen.py           # Chemistry generation
│   │   └── bio_gen.py            # Biology generation
│   ├── verifiers/
│   │   ├── sympy_verify.py       # Symbolic math verification
│   │   ├── solver_verify.py      # LLM solver verification
│   │   ├── chembio_verify.py     # Chemistry/Biology LLM-as-judge factual check
│   │   ├── calculator_check.py   # Calculator-free arithmetic validation
│   │   ├── structural.py         # Format/distractor checks
│   │   └── dedup.py              # FAISS embedding deduplication
│   ├── distractors/
│   │   └── computational.py     # Error-transform distractor generation + LLM plausibility filter
│   ├── diagrams/
│   │   ├── tikz_compiler.py      # LaTeX → PDF → SVG pipeline
│   │   ├── rdkit_renderer.py     # SMILES → SVG molecular structures
│   │   ├── matplotlib_gen.py     # Graphs, titration curves, etc.
│   │   ├── svg_templates/        # Pre-drawn biology SVG templates
│   │   └── tikz_templates/       # Parameterised TikZ templates
│   ├── quality/
│   │   ├── coverage_tracker.py   # Syllabus coverage tracking
│   │   ├── difficulty_balancer.py # 20/50/30 distribution
│   │   ├── difficulty_scorer.py  # Structural difficulty scoring (post-generation)
│   │   └── rubric_scorer.py      # LLM quality scoring
│   └── output/
│       ├── export.py             # JSON export for web platform
│       └── database.py           # SQLite/Postgres interface
├── data/
│   ├── past_papers/              # Raw ENGAA/NSAA/ESAT papers (PDFs)
│   ├── extracted/                # OCR'd question JSON files
│   ├── style_guide/              # Opus-extracted patterns (generated)
│   └── question_bank.db          # SQLite question database
├── scripts/
│   ├── classify_corpus.py        # Stage 1: Haiku corpus classification to spec codes
│   ├── extract_per_topic.py       # Stage 2+3: Opus per-topic pattern extraction
│   ├── ingest_papers.py          # PDF → structured JSON
│   ├── generate_batch.py         # Generate N questions (cron-triggered)
│   └── export_to_web.py          # Export question bank for website
└── tests/
    ├── test_generators.py
    ├── test_verifiers.py
    └── test_dedup.py
```

### 14.3.1 Database Schema (Qualitative)

The question bank database (SQLite for v1) stores everything the web platform needs to serve questions and everything the pipeline needs to track quality. The exact table structure, column names, and types are left to the coding agent's judgement. What matters is that the following data is captured:

**Per question:**
- Unique identifier
- Module (Maths 1, Maths 2, Physics, Chemistry, Biology)
- Topic and subtopic (e.g. "Mechanics > Inclined planes")
- Difficulty label (easy/medium/hard) AND structural difficulty score (numeric, from the difficulty scorer)
- Question text (with LaTeX markup for rendering)
- Five answer options (A–E)
- Correct answer letter
- Worked solution (with LaTeX)
- Diagram, if any (SVG content + what type: TikZ, RDKit, Matplotlib, template)
- Which template generated it (template ID from patterns)
- Which insight scenario was used, if any (scenario ID)
- Which LLM model generated it
- Quality rubric score (1–5)
- Verification results: did it pass calculator-free check, SymPy check, solver check, Chem/Bio factual check?
- Embedding reference (for FAISS deduplication lookups)
- Timestamp of creation

**Per generation batch:**
- Batch identifier
- Start/end timestamps
- Module targeted
- Questions generated, accepted, rejected counts
- Total API cost for the batch
- Model used

**Per question review (for future human review or feedback):**
- Question reference
- Reviewer (who/what)
- Score or verdict
- Notes
- Timestamp

This is intentionally qualitative. The coding agent should design the actual schema — normalisation level, indexes, foreign keys, etc. — based on what makes the queries simple and the web platform fast.

### 14.4 Generation Workflow (End-to-End)

**Phase 1: Setup (one-time, ~1 day)**

1. **Download and ingest the ESAT Content Specification PDF**
   - URL: `https://uat-wp.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/30103004/ESAT_Content_Specification_April2025.pdf`
   - Use `pdfplumber` to extract text, preserving section headings and bullet-point structure
   - Parse into structured JSON taxonomy with topic codes: `config/spec_taxonomy.json`
   - This is the authoritative source for what is in/out of scope for every module
   - Cost: ~$0 (local parsing, no API call needed)
   - See Section 10.6 for full details

2. **Install dependencies on VM:**
```bash
sudo apt install texlive texlive-latex-extra texlive-fonts-recommended
pip install rdkit sympy sentence-transformers faiss-cpu anthropic openai matplotlib pdfplumber
```

3. **Download and OCR past papers:**
- Source: [esat-tmua.ac.uk/esat-preparation-materials](https://esat-tmua.ac.uk/esat-preparation-materials) for ESAT specimen papers
- Source: [TutorChase ENGAA](https://www.tutorchase.com/past-papers/admissions-tests/engaa) and NSAA collections for 2016–2023
- Use `pdfplumber` to extract question text, options, and solutions
- Store as structured JSON in `data/extracted/`

4. **Run 3-stage pattern extraction:**
```bash
# Stage 1: Haiku classification
python3 scripts/classify_corpus.py \
  --input data/extracted/ \
  --taxonomy config/spec_taxonomy.json \
  --output data/classified/classified_corpus.json \
  --model claude-haiku-4.5

# Stage 2+3: Opus per-topic extraction (runs all ~36 topics)
python3 scripts/extract_per_topic.py \
  --classified data/classified/classified_corpus.json \
  --taxonomy config/spec_taxonomy.json \
  --output config/ \
  --model claude-opus-4.8
```
- Cost: ~$6–$8 total (see Section 10.2 for breakdown)
- Output per topic: `config/distractor_catalogue.<spec_code>.json`, `config/style_guide.<spec_code>.md`, `config/insight_scenarios.<spec_code>.json`

**Phase 2: Batch Generation (ongoing, nightly)**

OpenClaw cron triggers at 2 AM:
```bash
openclaw cron add \
  --schedule "0 2 * * *" \
  --name "ESAT nightly generation" \
  --message "Run: python3 /home/ubuntu/esat-gymnasium/scripts/generate_batch.py --batch 50 --module physics. Report results." \
  --agent esat-manager \
  --session isolated
```

`generate_batch.py` execution:
```
1. Load per-topic style guides + distractor catalogues + insight scenarios for target topic
2. Check coverage tracker → identify underrepresented topics
3. Check difficulty balancer → get target difficulty distribution
4. For each question in batch:
   a. Select template from question_patterns.json + matching insight scenario from insight_scenarios.<topic>.json
   b. Get generation directive (topic + difficulty)
   c. If template.generation_strategy == "solution_first":
      - Compute answer first via solution_algorithm + parameter values
      - Generate question text around the computed answer
      - Generate distractors via computational error transforms
   d. Else (question_first):
      - Call Haiku 4.5 (or GLM-4.5-Air) with template + directive → question JSON
   e. Run SymPy verification → if fails, regenerate (max 3 retries)
   f. Run solver verification → if fails, regenerate
   g. Run structural checks → if fails, regenerate
   h. Run structural difficulty scoring → compare vs target band → flag mismatch
   i. Run computational distractor pipeline → apply error transforms → LLM plausibility filter
   j. Generate diagram if needed (TikZ/RDKit/Matplotlib)
   k. Run dedup check (FAISS) → if duplicate, regenerate
   l. Run quality rubric → score 1–5
   m. If score ≥ 4: accept → add to database + FAISS index
   n. If score < 4: reject → log reason
5. Update coverage tracker + difficulty balancer
6. Output: batch_summary.json
```

**Error Handling & Diagnosability**

The pipeline does not need an elaborate retry/circuit-breaker system, but it must be designed so that failures are easy to diagnose without extensive debugging. Key principles:

- **Structured logging:** Every pipeline stage logs to a structured JSON file (one per batch) with: timestamp, stage name, question ID, status (success/fail), error type, raw LLM response on failure. If something breaks, the log tells you exactly where and why.
- **Save raw outputs:** Every LLM API response is saved to a `raw_outputs/` directory before parsing. If JSON parsing fails, the raw text is already on disk for inspection — no need to reproduce the failure.
- **Validation before insertion:** Every LLM response is validated against the expected JSON schema before being inserted into the pipeline. Malformed JSON is logged and the question is discarded (not retried blindly).
- **Per-question isolation:** A failure on one question never crashes the batch. Each question is processed independently; failures are logged and the batch continues.
- **Batch summary:** The `batch_summary.json` includes a `failures` section with: count by error type, sample error messages, and total API cost including wasted calls. This makes it obvious if rate limits, formatting issues, or content filters are causing problems.
- **Telegram alerting:** If a batch has >30% failure rate, the OpenClaw cron job sends a Telegram notification with the failure summary so issues are caught early.

**Phase 3: Export to Web Platform**

```bash
python3 scripts/export_to_web.py --output /var/www/esat-gymnasium/questions.json
```
- Exports accepted questions as JSON for the web frontend
- Includes: question text (with LaTeX), options, diagram SVGs, metadata
- Web platform reads JSON on page load or via API endpoint

### 14.5 Cost Projection (Complete System)

| Component | One-Time Cost | Ongoing Cost |
|---|---|---|
| Opus pattern extraction (3-stage per-topic: Haiku classification + Opus per-topic calls) | $6–$8 | — |
| TikZ template creation (Opus) | $5.00 | — |
| Biology SVG templates (manual/contractor) | ~$200 (one-time design) | — |
| Nightly generation (50 questions/night) | — | ~$0.30/night (Haiku Batch API) |
| Nightly generation (GLM-4.5-Air alternative) | — | ~$0.07/night |
| Deduplication + coverage tracking | — | $0 (local compute) |
| Diagram generation | — | Included in generation cost |
| Vision verification (GLM-4.6V-Flash) | — | $0 (free tier) |
| VM (Oracle Cloud free tier) | — | $0 |
| **Monthly total (Haiku path)** | — | **~$9/month** |
| **Monthly total (GLM path)** | — | **~$2/month** |

**At 50 questions/night, the system generates 1,500 questions/month for ~$2–$9.**

After 3–4 months, the question bank reaches 5,000+ questions at a total API cost of $14–$16.

### 14.6 Scaling Beyond 5,000 Questions

Once the initial bank is established:

1. **Increase batch size:** 100 questions/night = 3,000/month
2. **Add modules:** Generate for all 5 modules concurrently
3. **Parameter rotation:** Systematically cycle through parameter spaces to ensure variety
4. **Feedback integration:** Use user performance data to identify weak areas and generate targeted questions
5. **Periodic pattern refresh:** Re-run Opus extraction annually with new ESAT papers (when UAT-UK publishes them)
6. **Fine-tuning option:** Once 2,000+ verified questions exist, fine-tune a smaller model on them for even cheaper generation

The system scales linearly — 10,000 questions costs ~2× the API budget of 5,000. At the GLM-4.5-Air price point, even 50,000 questions costs under $100 in API fees.

### 14.7 Alternative: Full OpenClaw-Managed (No Python Pipeline)

If the user prefers to avoid maintaining a Python codebase entirely, the generation pipeline can run **entirely within OpenClaw**:

- Cron job triggers agent with a detailed skill file
- Agent uses `exec` tool to run Python snippets (SymPy, RDKit, FAISS) inline
- Agent calls LLM APIs via its native multi-model routing
- Agent stores questions as JSON files in its workspace
- Agent sends Telegram summary after each batch

**Pros:**
- Zero Python codebase to maintain
- All logic in skill files (markdown)
- Native Telegram integration for monitoring
- Leverages existing OpenClaw infrastructure

**Cons:**
- Slower (agent loop overhead per question)
- Less precise control over error handling
- Token cost for agent's own reasoning (planning, deciding)
- Harder to run truly parallel generation

**Recommendation:** Start with the hybrid approach (OpenClaw cron + Python script). If the Python pipeline proves hard to maintain, migrate to full OpenClaw management.

---

## Appendix C: ESAT Symbols, Notation & Units Reference

This reference defines what notation and units are valid in generated ESAT questions. The LLM generation prompt must include these conventions; the calculator-free checker validates them. Full research with worked examples is in `calculator-free-research.md`.

### C.1 Key Conventions

| Convention | Rule |
|---|---|
| g | **10 N kg⁻¹** — always, per spec P3.5b |
| Standard angles | 0°, 30°, 45°, 60°, 90° only (unless estimation question) |
| Surds | Tested skill — √12 → 2√3, rationalise denominators. Allowed in answers. |
| Estimation | Tested (M2.14). Questions must use "estimate" or "approximately". |
| Answer precision | Max 3 significant figures |
| Natural log (ln) | **NOT in ESAT spec — do not use** |
| Compound units | Negative indices (m s⁻¹), not slash (m/s) |
| Vector notation | Bold type (**F**, **v**). No arrows or hats. |
| Physical constants | Must be given in question stem (SHC, speed of light, etc.) |

### C.2 Valid Units by Module

**All modules:** SI base units (kg, m, s, °C, A, mol) with standard prefixes (n, μ, m, c, d, k, M, G).

| Module | Common Units | Units NOT in ESAT |
|---|---|---|
| Maths 1 & 2 | m s⁻¹, m s⁻², kg m⁻³, Pa, N m⁻² | — |
| Physics | N, J, W, C, V, Ω, Hz, T (if F=BIL), J kg⁻¹ °C⁻¹ | kWh, eV, MeV, atm, mmHg, bar, calorie |
| Chemistry | g mol⁻¹, mol dm⁻³, g dm⁻³, dm³, cm³, kJ mol⁻¹, °C, K | M (molarity), atm |
| Biology | cm³ s⁻¹, organisms per m², %, cm³ min⁻¹ | — |

### C.3 Greek Letters Used

| Letter | Usage | Module |
|---|---|---|
| θ, α, β | Angles | Maths, Physics |
| λ | Wavelength | Physics |
| ρ | Density | Physics |
| μ | Friction coefficient (given in question) | Physics |
| Δ | Change in quantity | All |
| ω | Angular velocity | Physics |
| σ | Stress, surface tension | Physics |
| ε | Permittivity (given in question) | Physics |
| γ | Gamma radiation, ratio | Physics |
| β | Beta particle/radiation | Physics, Chemistry |

### C.4 Notation Rules by Module

- **Maths 1:** degrees for angles, no calculus, no set notation, no interval notation
- **Maths 2:** radians (π/6, π/4, π/3, π/2), calculus notation (dy/dx, ∫), binomial coefficients (ⁿCᵣ), factorials (n!), modulus (|x|)
- **Physics:** circuit symbols, force diagrams with labelled arrows, nuclear equations (²³⁸₉₂U → ²³⁴₉₀Th + ⁴₂He), nuclide notation (ᴬ_ZX)
- **Chemistry:** state symbols (s, l, g, aq), isotope notation (¹²₆C), oxidation states (iron(III)), Ar/Mr, ΔH, Ea, electron configuration (2,8,8,1)
- **Biology:** allele notation (Tt, TT, tt), Punnett squares, pedigree notation, DNA bases (A, T, G, C), sex chromosomes (XX, XY)

---

*End of Report*