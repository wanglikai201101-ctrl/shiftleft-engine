# ShiftLeft Engine · Left-Shift（左移·来福）

> **Feed in a requirement, and let AI take care of the rest.**

> A requirement-driven, test-shift-left engineering platform — starting from source code and requirements, it automatically produces traceable knowledge-base docs (10 dimensions), a bidirectional traceability graph, and MCP-Ready test cases. This release ships as the "GSD Knowledge Base open-source subset".

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python](https://img.shields.io/badge/Python-3-blue.svg)](https://www.python.org/)
[![Claude Code Skills](https://img.shields.io/badge/Claude%20Code-Skills-orange.svg)](https://claude.com/claude-code)

> **🌐 Language / Languages:** [简体中文](README.md) · [繁體中文](README.zh-TW.md) · **English** · [日本語](README.ja.md)

## 🎬 Demo Video

[Click to watch the full demo](https://youtu.be/stfLoSjn8Go)

> 🧪 **A real end-to-end pipeline run: 130 agents · 1h01m · status done (not fail)** — pre-coding investigation → frontend/backend development + auto checks → docs/graph maintenance → automated ops deployment → smoke tests → real UAT → report. The whole flow genuinely ran end-to-end; screenshots below.

## 🧩 What is ShiftLeft Engine?

ShiftLeft Engine is a **requirement-driven, test-shift-left engineering platform** (continuously evolving). What this release open-sources is one genuinely usable, independently deployable piece of it: **GSD Knowledge Base** — opening up the most foundational engineering capability in "from requirement to verification", so every team can bring the **requirement → development → docs → graph → test cases** automated chain into its own projects: 27 self-built `gsd-kb-*` skills covering knowledge-base engineering and test-case generation across requirements/docs/graph/test cases; plus **9 gsd-core (MIT) development skills** (quick / debug / spike / code-review / plan-phase / execute-phase, etc., inspired by gsd-core, adopted selectively rather than in full), rounding out the development/engineering-methodology side.

### Core Philosophy

> **Say one sentence, and leave the rest to AI.**
>
> This is the new paradigm of the AI era: **AI is the primary executor** — from requirements to coding, testing, docs, and deployment, AI executes, maintains, and self-heals everything on its own.
>
> Humans only feed in requirements and acceptance results. **AI-driven test shift-left** makes quality assured from the source, with the whole chain traceable.

### 🚧 Current Status

> The following are the capabilities **already implemented in the full product** (this open-source subset only contains the KB engineering layer — see "Current open-sourced capabilities" and "Why open-source only the wheels").

- ✅ **Full pipeline**: input requirement → confirm changed modules → elaborate the requirement (current-state investigation) → code investigation produces a Plan → fast development per the Plan (initial auto-checks along the way) → after development, parallel Fill (graph + docs + automated ops + element-fingerprint append) → smoke tests (continuous fixing on failure) → UAT tests (faithful to requirement / faithful to quality) → report
- ✅ Graph visualization (offline D3 interactive graph)
- ✅ AI-assisted repair (auto-fixing of smoke / UAT failures)
- 🔄 Continuous refinement: test coverage analysis
- 📋 Planned: more language support; later add one more UAT round, with a second fixing loop on failure

### 🎯 Future Plans

- **Phase 1**: Test shift-left engineering platform (current)
- **Phase 2**: Apply to the app development layer (planned)
  - Extend this model to mobile development
  - Deliver a closed loop of requirement → coding → testing → release
  - Support cross-platform development (iOS / Android / Flutter, etc.)

> **This is a continuously evolving project — follow along and join in!**

---

## 🖼️ Full-Pipeline Run Screenshots (Real Run Evidence)

> The screenshots below come from one full real pipeline run (**130 agents · 1h01m · status done**), arranged by stage.
> Note: the "coding → deployment → smoke → UAT → report" loop belongs to the full product vision (automated deployment is not shipped with this open-source subset). The screenshots demonstrate the full product genuinely running; for what this open-source subset can run independently, see "Current open-sourced capabilities".

| ① Pre-coding investigation | ② Frontend/backend dev + check | ③ Doc maintenance |
|---|---|---|
| ![Pre-coding investigation](docs/101编码前的调查.jpg) | ![Frontend/backend dev + check](docs/102前后端开发+check.jpg) | ![Doc maintenance](docs/103文档维护.jpg) |

| ④ Graph maintenance | ⑤ Automated ops deployment | ⑥ Smoke tests |
|---|---|---|
| ![Graph maintenance](docs/104维护图谱.jpg) | ![Automated ops deployment](docs/105自动运维部署.jpg) | ![Smoke tests](docs/106冒烟测试.jpg) |

| ⑦ Real UAT tests | ⑧ UAT test results | ⑨ Report generation |
|---|---|---|
| ![Real UAT tests](docs/107真实UAT测试.jpg) | ![UAT test results](<docs/111 UAT-测试结果.jpg>) | ![Report generation](docs/108产生报告.jpg) |

| ⑩ Knowledge base + graph | ⑪ Doc materialization | ⑫ Full payload log |
|---|---|---|
| ![Knowledge base + graph](docs/109知识库+图谱.jpg) | ![Doc materialization](docs/110文档具像化.jpg) | ![Full payload log](docs/113完整报文.jpg) |

| ⑬ Proven by trce | ⑭ Proven by video |
|---|---|
| ![Proven by trce](docs/111视频-trce为证.jpg) | ![Proven by video](docs/112视频为证.jpg) |

---

## 🧩 Why Open-Source Only the "Wheels"? — The Complete Puzzle, Right Here

It's not that we don't want to hand over the whole train — this layer is deliberately the only one open-sourced: **I've broken the entire "test shift-left engineering platform" train into a complete jigsaw puzzle, and every puzzle piece (wheel) is placed right here** — every reusable component of the "requirement → development → docs → graph → test cases" automated chain: 27 `gsd-kb-*` skills + the Python engine + 9 gsd-core (MIT) development skills. Every piece installs and works independently.

> Fit these wheels together piece by piece, and what you assemble is exactly the test shift-left engineering platform from the video above — **a real run of 130 agents · 61 minutes · done across the whole chain**. One jigsaw puzzle, one complete train.

> The whole puzzle is laid out here for one reason: to find **kindred spirits** — people who can see this "test shift-left engineering platform" train and are willing to roll the pieces up, piece by piece, onto the track.

> The wheels are already in your hands. If you know full well that putting them together makes a complete train, yet you'd rather just look and not build — then this train will just have to depart without you 😄

**What does the train look like?** → [Demo video](https://youtu.be/stfLoSjn8Go) + the 14 real-run screenshots above.

> **Scope of this release**: every puzzle piece (wheel) above is delivered in this repo and can be assembled independently; the further-upstream "end-to-end orchestration and deployment" locomotive belongs to the full product's subsequent iterations. For anyone who wants to assemble the whole train, starting from these puzzle pieces is the fastest way aboard.

---

## 🎯 Why Fill?

### The Pain Point: Problems in Traditional Development

```
❌ Verbal agreement: the PM says "add a field here"
   → The developer adds it
   → QA never knows
   → Three months later, no one remembers why

❌ AI project black box:
   → AI worked on the project for half a year
   → The code runs
   → But no one knows why it was designed this way
   → Unmaintainable — the only option is to rewrite

❌ No traceability:
   → Requirements change
   → No idea which APIs are affected
   → No idea which tests are affected
   → Only full regression, wasting time
```

### The Solution: Fill's Bidirectional Traceability Graph

```
Requirement (REQ-xxx)
    │
    ├──→ API (API-xxx)
    │    │
    │    ├──→ Database (Table-xxx)
    │    │    │
    │    │    └──→ Field-level read/write traceability
    │    │
    │    └──→ Frontend page (Page-xxx)
    │         │
    │         └──→ UI element (data-testid)
    │
    └──→ Test point (TP-xxx)
         ├──→ API test cases
         ├──→ UI test cases
         └──→ E2E test cases
```

### Fill's Real Value

| Traceability direction | Value | Served for |
|---------|------|----------|
| Requirement → API | Which APIs does this requirement implement? | Devs, QA, PM |
| API → Database | Which tables does this API read/write? | Devs, DBA |
| API → Page | Which pages call this API? | Frontend, QA |
| Requirement → Test point | What does this requirement need testing? | QA |
| Change → Impact | Change this API — which requirements are affected? | Everyone |
| Test → Regression | Which requirements does this test cover? | QA, PM |

### Why Is Fill Placed in the Middle?

- **After coding**: there's code to extract docs from
- **Before testing**: the graph determines the testing scope
- **During maintenance**: the graph records design decisions

### Core Value

> **Make AI's execution traceable across the whole chain.**
>
> - Requirements are grounded and verifiable
> - Development has a graph to rely on
> - Testing has a map to follow
>
> **That's exactly why the Fill stage sits in the middle!**

---

## ⚖️ The Honesty Principle

Test shift-left has a critical **honesty problem**:

### Two Testing Strategies

| Strategy | Approach | First-pass success rate | Notes |
|------|------|-----------|------|
| **Faithful to the requirement** | Never test what isn't specified | ~95% | Only test what the requirement explicitly asks for |
| **Pursuing quality** | Free rein | ~70% | Also test boundaries, exceptions, performance, etc. |

### Why Does "Faithful to the Requirement" Deliver a 95% Success Rate?

```markdown
# Requirement: return order_id after order creation succeeds
✅ Test: POST /api/orders → 200 + order_id

# Requirement doesn't mention: what about concurrent creation
❌ No test: concurrent-conflict handling (unless the requirement explicitly asks)

# Requirement doesn't mention: what about an extremely large amount
❌ No test: amount boundaries (unless the requirement explicitly asks)
```

### Recommendation

- ✅ Explicitly required by the requirement → 100% tested
- ⚠️ Implied by the requirement → 95% coverage
- ❌ Not mentioned in the requirement → not tested (unless separately agreed)

**Why?**
- The goal of test shift-left is to "quickly verify whether the requirement is implemented"
- Not to "chase perfect code"
- If you want quality on top, you need an extra "quality enhancement" stage

---

## 🔄 Current Open-Sourced Capabilities · KB Engineering Workflow

The complete "requirement → coding → deployment → smoke → UAT → report" automated loop is the **full product vision** of ShiftLeft Engine; its orchestration pipeline iterates with the full product's cadence and is **not shipped with this repo in this release**. What this release opens is the most foundational engineering layer in that loop — "knowledge base + graph + test-case generation" — made up of **27 `gsd-kb-*` skills** and **9 gsd-core (MIT) development skills**, ready to deploy on any project:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1 · Initialize KB + graph                                     │
│  /gsd-kb-init --source <source> --module <module> --output docs/kb  │
├─────────────────────────────────────────────────────────────────────┤
│  Step 2 · Multi-dimension Fill (docs + graph)                       │
│  /gsd-kb-fill + 14 fill sub-skills (10-dimension docs + graph)      │
├─────────────────────────────────────────────────────────────────────┤
│  Step 3 · Test-case generation (MCP-Ready JSON)                     │
│  /gsd-kb-gen-tests-{api,e2e,ui}                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Step 4 · Element-fingerprint injection                             │
│  /gsd-kb-enforce-locators (data-testid standardization)             │
├─────────────────────────────────────────────────────────────────────┤
│  Step 5 · Query · Repair · Incremental absorb                       │
│  /gsd-kb-query · /gsd-kb-repair-orphans · /gsd-kb-absorb            │
└─────────────────────────────────────────────────────────────────────┘
```

### Step 1: Initialize (init)

```
Source code → reverse-scan APIs/tables/pages/jobs → generate doc skeleton + graph
/gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb
```

### Step 2: Multi-Dimension Fill (fill)

```
Document skeleton
    │
    ├──→ Phase 1: /gsd-kb-fill-tech       ← Python engine batch-fill (sub-second static AST extraction)
    └──→ Phase 2: /gsd-kb-fill-ai         ← AI multi-agent orchestration (deep semantic fill in minutes)
          ├── 10-dimension docs: requirements · apis · storage · pages · jobs
          │   config · permissions (authn/authz) · error-handling · integration · tech
          ├── Extras: from-prd (absorb original requirements, fill authoritative business context)
          └── Graph: graph (build + offline D3 visualization) · graph-links (backfill bidirectional traceability links)
```

### Step 3: Test-Case Generation (gen-tests)

```
/gsd-kb-gen-tests-api    → Multi-step chained API contract test cases (MCP-Ready JSON)
/gsd-kb-gen-tests-e2e    → Business-flow / edge-case / rollback-consistency cases based on a depends_on DAG
/gsd-kb-gen-tests-ui     → UI test cases based on data-testid (Playwright semantic selectors)
```

Template-driven: each sub-skill reads `templates/{API,E2E,UI}-TEST-TEMPLATE.json` and outputs MCP-Ready structured JSON. In the full product, execution is handled by the **QA multi-agent orchestration and execution system** (admission → cluster dispatch → execution in real environments → result feedback). This open-source subset only opens "test-case generation"; the execution system is not bundled (to be decided later based on how open-sourcing evolves).

### Step 4: Element-Fingerprint Injection (enforce-locators)

```
Scan frontend components → inject standardized data-testid (interactive elements + validation/error-message elements)
→ Make real-browser UI tests "fast as lightning, solid as rock"
```

### Step 5: Query · Repair · Absorb

```
/gsd-kb-query            → Graph query: impact analysis / requirement traceability / doc lookup — precise context
/gsd-kb-repair-orphans   → Repair orphaned links in the graph (orphan nodes, report-only cross-check)
/gsd-kb-absorb           → Incrementally absorb .planning/ artifacts into KB docs (incremental patch, not a full rewrite)
```

---

## 🏗️ Architecture Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              ShiftLeft Engine · Open-source subset architecture             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Inputs                                                                     │
│  ┌ ──────────────────── ┐    ┌ ──────────────── ┐    ┌ ─────────────── ┐    │
│  │ Source code          │    │ Requirement docs │    │ ENV-CONFIG      │    │
│  │ (multi-language code) │   │ (REQ-xxx)        │    │ (JSON contract) │    │
│  └ ──────────┬───────── ┘    └ ────────┬─────── ┘    └ ───────┬─────── ┘    │
│              │                         │                      │             │
│              ▼                         ▼                      ▼             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ SKILL layer · 27 gsd-kb-* (Claude Code Skills, Markdown)              │  │
│  │ init → fill (+14 sub-skills) → gen-tests-{api,e2e,ui}                 │  │
│  │ enforce-locators → query · repair-orphans · absorb                    │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│  ┌───────────────────────────────────┴───────────────────────────────────┐  │
│  │ Python engine layer · knowledge-base (packages, 12 subcommands)       │  │
│  │ Zero third-party deps · scaffold / batch-fill / decompose /           │  │
│  │ fill / check / trace / index / graph / regression                     │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│  ┌───────────────────────────────────┴───────────────────────────────────┐  │
│  │ gsd-core (MIT) dev skills · 9                                         │  │
│  │ quick · debug · spike · code-review · plan-phase · ...                │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │   Outputs                                                             │  │
│  │ KB docs (10 dimensions) · graph.json + graph.html (D3)                │  │
│  │ Test-case JSON (API/UI/E2E, MCP-Ready) · ENV-CONFIG.json              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

> The full product's "🧠 orchestration layer (Pipeline Orchestrator) + MCP agent cluster" is full-product capability and is not shipped with this repo (demo in the video above; boundaries in "Why open-source only the wheels").

---

## 🎯 Core Capabilities

| Capability | Rating | Description |
|------|------|------|
| Fill bidirectional traceability graph | ⭐⭐⭐⭐⭐ | 10-dimension holographic mapping — the whole chain from requirement → API → storage → page → test point is traceable |
| Stable element fingerprints | ⭐⭐⭐⭐⭐ | Automatic data-testid injection (enforce-locators) — fast and stable real-browser tests |
| Test-case generation | ⭐⭐⭐⭐⭐ | API / UI / E2E three formats, template-driven, MCP-Ready JSON executable as-is |
| JSON contract | ⭐⭐⭐⭐⭐ | ENV-CONFIG.sample.json defines the deployment → testing standard contract; downstream parses it uniformly |
| Graph query + impact analysis | ⭐⭐⭐⭐⭐ | gsd-kb-query: change impact scope, requirement traceability, doc lookup — answers in seconds |
| Orphan-link repair | ⭐⭐⭐⭐☆ | graph repair-orphans auto-adds edges, sweeping up leftover orphan nodes |
| Incremental absorption | ⭐⭐⭐⭐☆ | gsd-kb-absorb patches incrementally instead of rewriting existing docs wholesale |
| Zero third-party dependency engine | ⭐⭐⭐⭐⭐ | Python engine with 12 subcommands, pure standard library — install once, run anywhere |
| Multi-stack source parsing | ⭐⭐⭐⭐☆ | scaffold reverse-scans multiple languages (API/ORM/Page/Job) with automatic sub-project discovery |

---

## 📦 Product Components (Design, Revealed as the Full Product Evolves)

The following 4 components are **full-product** "ShiftLeft Engine" component interface designs (revealed as the full product evolves; not delivered in this repo):

- **`@shiftleft-engine/fill-graph`** — type definitions and query interface for the Fill bidirectional graph (design)
- **`@shiftleft-engine/locator-generator`** — automatic element-locator injection tool (design)
- **`@shiftleft-engine/cli-interface`** — CLI command parsing and argument validation spec (design)
- **`@shiftleft-engine/report-formatter`** — comprehensive report generation template (design)

> The TypeScript code, npm package interfaces, and `shiftleft-engine` CLI usage shown in earlier README versions were all full-product design drafts (to be revealed with later versions per the product cadence) — for what's genuinely usable in this repo, see "Quick Start" below.

---

## 🚀 Quick Start

### Installation

```bash
git clone <this-repo-url>
cd <this-repo>
bash install-kb.sh  # Run directly at the release repo root; in a source clone, use bash release/install-kb.sh or bash scripts/install-kb.sh
```

- Default **copy** mode (safe — moving the repo won't produce broken links); `--link` creates symlinks (development mode — editing the source applies immediately); `--target` changes the target directory
- What gets installed: `gsd-kb-*` skills + 9 gsd-core (MIT) development skills → `~/.claude/skills`; the gsd-core engine → `~/.claude/gsd-core`; the Python engine → `~/.claude/knowledge-base`
- Locations: the 27 `gsd-kb-*` skills live at the repo root `skills/`; the 9 gsd-core (MIT) development skills ship with the release package (`release/release-skills/` in a source clone, `release-skills/` at the release package root) — the repo-root `skills/` contains only the 27 `gsd-kb-*` skills. See `release/PACKAGE.md` for the complete boundary

**Restart Claude Code after installation** and the `/gsd-kb-*` slash commands will be available.

> This is the project's first open-source release. If you run into any problem during installation or usage, feedback (filing an issue) is most welcome — I'll take care of it as soon as I can.

### Minimal Viable Path (init → fill-ai → gen-tests-e2e)

```bash
# 1. Initialize KB + graph (reverse-scan to generate the doc skeleton)
/gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb

# 2. AI multi-agent deep fill (10-dimension docs + graph)
/gsd-kb-fill-ai --module your-project --source C:/Code/your-project/backend \
                --frontend C:/Code/your-project/frontend --output docs/kb

# 3. Generate MCP-Ready E2E test cases
/gsd-kb-gen-tests-e2e --module your-project --output docs/kb
```

### Python Engine

```bash
cd knowledge-base         # Release repo root; in a source clone, cd release/knowledge-base
python3 -m packages.cli --help    # 12 subcommands: decompose / fill / check / trace /
                                  # scaffold / batch-fill / graph / index / regression / ...
```

### ENV-CONFIG Contract

See [`samples/ENV-CONFIG.sample.json`](samples/ENV-CONFIG.sample.json) for a sample of the deployment → testing JSON contract; see [`PACKAGE.md`](PACKAGE.md) for the complete release boundary (`release/PACKAGE.md` inside a source clone).

---

## 📐 Tech Stack

- **Engine language**: Python 3 (zero third-party dependencies, pure standard library)
- **Skill layer**: Claude Code Skills (Markdown instructions + templates)
- **Data contract**: JSON (ENV-CONFIG / test cases / graph.json)
- **Graph visualization**: D3.js (offline; interactive force-directed graph in graph.html)
- **Installer**: bash (install-kb.sh — install straight from the open-source repo)

---

## 🤝 Contributing

Contributions are welcome! Please first read [`release/PACKAGE.md`](release/PACKAGE.md) to understand the open-source release boundary.

### Development Environment

```bash
# Clone the repo (fill in the actual repo address at release time)
git clone git@github.com:<your-org>/<repo>.git

# Sync both copies (important!)
# skills/ is the source; release/skills/ is the release copy — whenever you change a skill, sync both,
# otherwise the release diverges from the source (same for repo skills vs. the global ~/.claude copy)

# Run the Python engine directly under knowledge-base/
cd knowledge-base
python3 -m packages.cli --help
```

---

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

**Why Apache-2.0?**
- Permissive license — maximizes adoption and community reach
- Includes patent grant and trademark protection clauses, balancing contributors' rights
- Compatible with the gsd-core (MIT) license that inspired this project; attribution statements can be kept

> This project contains content derived from [gsd-core](https://github.com/open-gsd/gsd-core) (MIT License); see [NOTICE](NOTICE).

---

## 📊 Project Stats

- **Skills**: 27 `gsd-kb-*` (14 of which are fill sub-skills covering 10-dimension docs + graph)
- **Python engine**: 12 subcommands, zero third-party dependencies
- **Knowledge graph**: 10-dimension bidirectional traceability + offline D3 visualization
- **Test cases**: three-format generation (API / UI / E2E), MCP-Ready JSON
- **Development skills**: 9 built-in gsd-core (MIT) skills

---

## 🔗 Related Links

- [Demo video](https://youtu.be/stfLoSjn8Go)
- [Open-source release notes](release/PACKAGE.md)

---

## 🙏 Acknowledgements

### Inspiration

This project's architecture design and some utility functions draw on the following excellent open-source projects:

- **[GSD Core](https://github.com/open-gsd/gsd-core)** - a meta-prompting, context-engineering, and spec-driven development system
  - This project's knowledge-graph query and doc generation capabilities are inspired by GSD Core
  - The development-side skills (gsd-quick / gsd-debug / gsd-spike / gsd-code-review / gsd-plan-phase, among the 9) are embedded directly from gsd-core
  - GSD Core is MIT-licensed; this project extends its sincere gratitude

### Tech Stack Acknowledgements

Thanks to the following open-source projects:
- [Python](https://www.python.org/)
- [D3.js](https://d3js.org/)
- [Claude Code](https://claude.com/claude-code)
- [Bash](https://www.gnu.org/software/bash/)

---

## 🗺️ Roadmap

### Done

- ✅ Requirement-driven KB engineering pipeline (gsd-kb-init → fill → graph)
- ✅ Fill bidirectional traceability graph (10 dimensions + offline D3 visualization)
- ✅ Graph visualization (interactive force-directed graph in graph.html)
- ✅ Stable element fingerprints (data-testid injection, enforce-locators)
- ✅ API / UI / E2E test-case generation (MCP-Ready JSON)
- ✅ AI-assisted repair (auto-fixing of smoke / UAT failures)
- ✅ Python engine with 12 subcommands (zero third-party dependencies)
- ✅ One-click installer (install-kb.sh)

### In Progress

- 🔄 Test coverage analysis (deepening coverage)

### Planned

- 📋 QA multi-agent orchestration and execution system (the test-shift-left execution side; to be decided based on how open-sourcing evolves)
- 📋 npm distribution of `@shiftleft-engine` components (open-source subset → standalone packages)
- 📋 More language support
- 📋 Later: one more UAT round after UAT passes, with a second fixing loop on failure
- 📋 Performance-testing integration (K6)
- 📋 Mobile app development support (Phase 2)
- 📋 Multi-person collaboration mode

### Future Vision (Phase 2)

> **Apply this model to the app development layer**
>
> - Deliver a closed loop of requirement → coding → testing → release
> - Support cross-platform development (iOS / Android / Flutter, etc.)
> - Integrate CI/CD pipelines
> - Support multi-team collaboration

---

## 💬 Contact

- **Email**: wanglikai201101@gmail.com
- **GitHub**: [@wanglikai201101-ctrl](https://github.com/wanglikai201101-ctrl)

---

## 📌 Copyright

**© 2026 ShiftLeft Engine · Licensed under the Apache License 2.0**

*This repository is a personal independent project and involves no company trade secrets.*

*Architecture designed with inspiration from GSD Core; thanks to the original authors for their open-source contributions.*
