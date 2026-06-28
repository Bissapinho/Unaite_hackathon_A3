# Agentic Ontology for SMBs

> An agentic system that **builds the ontology layer of a small business** from its
> scattered data (ERP, TMS, internal database, Excel, PDF, emails), then lets an acquirer
> **query the company in natural language**.
>
> *"We turn any SMB into a navigable map in 10 minutes, so acquirers understand what
> they're buying."*

Hackathon project (track **The Next DecaCorn**). Demo company: a **regional transport
SMB**. The reference technical spec lives in [`CLAUDE.md`](CLAUDE.md); the data
documentation in [`DATA_README.md`](DATA_README.md).

---

## How to use it

> **TL;DR — to explore the ontology, just run the app.** The repo already ships with the
> compiled ontology in `outputs/`, so you do **not** need to run the ingestion pipeline.
> The full agentic build is slow (several minutes, ~$7 in tokens) and is only needed if you
> want to *re-generate* the ontology from the raw sources. Go straight to **Quick start**.

### Setup (Python 3.11+)

**macOS / Linux**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # create your .env from the template
open .env                   # (or: nano .env) — paste the ANTHROPIC_API_KEY after "ANTHROPIC_API_KEY="
```

**Windows (PowerShell)**
```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # create your .env from the template
notepad .env                # paste the ANTHROPIC_API_KEY after "ANTHROPIC_API_KEY="
```

> The key (provided in the submission form) goes on the `ANTHROPIC_API_KEY=` line in `.env`,
> with no quotes and no spaces, e.g. `ANTHROPIC_API_KEY=sk-ant-...`.

### Quick start — run the app (recommended)
This loads the pre-built ontology graph and lets you query it via System B. **This is the
path you want.**
```bash
python3 -m ui.app                # → http://127.0.0.1:5000  (real System B, ~35 s/question)
```

Optional mocked mode (instant SH-2049 answer, front-end dev, no key):
```bash
UI_MOCK=1 python3 -m ui.app                      # macOS / Linux
```
```powershell
$env:UI_MOCK=1 ; python -m ui.app               # Windows (PowerShell)
```

Questions to ask: the flagship question *"Is there a problem with a delivery?"* (surfaces
the SH-2049 incident by scoring), or structural questions (*"what does my revenue depend
on?"*, *"who are the key people?"*, *"what is my customer concentration?"*).

### (Optional) Rebuild the ontology from scratch
You only need this to **re-compile** the ontology from the raw sources — it is **not**
required to use the product. Heads-up: the ingestion pipeline is **long and token-heavy**
(the agentic extractor runs 8 LLM passes over all sources).

```bash
# 1. (Re)generate the synthetic data — idempotent, fast, no key
python3 data/generate_all.py     # produces all dumps (Odoo, Dashdoc, SQLite, Excel, PDF, emails)
python3 data/validate.py         # checks consistency (83/83 PASS expected)

# 2a. Deterministic oracle (no LLM, no key) — reference, fast
python3 -m system_a.build_ontology              # → outputs/ontology.json

# 2b. Agentic extractor (LLM, requires ANTHROPIC_API_KEY) — SLOW (~minutes, ~$7)
python3 -m system_a_agents.run                  # full pipeline (8 passes) → outputs/ontology.agentic.json
python3 -m system_a_agents.run --dry-run        # P0 only, NO key (plumbing test)
python3 -m system_a_agents.run --passes p2,p3   # replays a subset (reloads the blackboard)
```

Once rebuilt, query it the same way: run the app (Quick start above).

---

## What it does

An SMB stores its reality in silos that don't talk to each other: operations in a TMS,
finance in an ERP, ad-hoc fixes in a SQL database, Excel and PDF files lying around, a full
inbox. **Nothing is connected.**

The system ingests this heterogeneous chaos and turns it into a **queryable business
ontology** — a living map of the whole company across three connected layers:

- **Operational & commercial** — customers, orders, invoices, products, routes, fleet,
  carriers, suppliers (*the flow of activity*);
- **Human structure / HR** — the company, its director, employees, their roles, the org
  chart, key people (*who keeps the business running*);
- **Finance** — total revenue and customer concentration, margin, payroll, fleet costs,
  cash and payment lag (*financial health*).

Every entity and relationship carries its **provenance**: `sources`, `confidence` and
`evidence`. Anything *reconstructed by inference* (e.g. the org chart) carries a lower
confidence and an `open_question` — the ontology states what it **knows** vs what it
**infers**.

---

## How it works — two systems

The A/B boundary is sharp: **A builds, B queries.**

```
   SOURCES                  SYSTEM A — COMPILER                  SYSTEM B — AGENT
┌────────────────┐      ┌──────────────────────────┐      ┌──────────────────────┐
│ Odoo (ERP)      │      │  specialized passes:      │      │ User asks a question  │
│ Dashdoc (TMS)   │      │  Extraction → Profiler →  │      │   │                   │
│ SQLite annex    │ ───▶ │  Entity → Relationship →  │ ───▶ │ Agent (Opus 4.8)      │
│ Excel / PDF     │      │  Attribute → Architect →  │ json │ calls NetworkX TOOLS  │
│ emails (.eml)   │      │  Critic → Validation      │      │ (query)               │
└────────────────┘      └──────────────────────────┘      └──────────────────────┘
                          → outputs/ontology.json            → answer + evidence
                            + NetworkX graph                    + proposed actions
```

### System A — the ontology compiler
Designed as a **compiler** (specialized passes orchestrated by a deterministic supervisor),
not as a swarm of chattering agents. Each pass **proposes** elements and **attaches its
evidence**; the whole is assembled, criticized, then published. Non-negotiable pattern:
`propose → validate → Critic attacks → publish`.

It comes in **two stages**:
- **Deterministic oracle** ([`system_a/`](system_a/)) — no LLM, serves as reference.
- **Agentic extractor** ([`system_a_agents/`](system_a_agents/)) — Claude Agent SDK,
  passes p0→p7, supervisor + blackboard, visible logs. Produces
  [`outputs/ontology.agentic.json`](outputs/ontology.agentic.json) (**~242 entities /
  356 relationships**, ~99.8% convergence vs oracle).

Key technical point: **the org chart is exposed in no source** (realistic). A
**reconstructs** it by cross-referencing the title hierarchy, email signatures/escalations,
and operational cross-references (see [CLAUDE.md §6](CLAUDE.md)).

### System B — the conversational agent
Its **only role: query** the ontology published by A. It reloads `ontology.json` into a
NetworkX graph, then reasons through **generic query tools** — `find_nodes`,
`get_neighbors`, `shortest_path`, `get_subgraph`, `compute_impact`,
`score_delayed_shipments`, `articulation_points`, `centrality`. It answers in natural
language with its **evidence chain** and proposes **actions (as text, never executed)**.

B does **real reasoning**: to single out the critical shipment SH-2049, it retrieves all
delayed shipments and **scores** them — it does not read a pre-chewed `is_hot` field.

### The demo interface
A **Flask** server ([`ui/`](ui/)) serving an animated canvas viz (graph of the 3 colored
layers) plus a chat wired to the real System B via `POST /ask`. The `node_ids` from the
answer drive the **synchronized highlighting** of the map (zoom on the critical path).

---

## The pre-built ontology

The repo ships with an **already compiled** ontology, committed in `outputs/` — no need to
replay the pipeline to explore the product:

| File | Contents |
|---|---|
| [`outputs/ontology.json`](outputs/ontology.json) | Output of the **deterministic oracle** (factual reference) |
| [`outputs/ontology.agentic.json`](outputs/ontology.agentic.json) | Output of the **agentic extractor** (~242 entities / 356 relationships) — this is the one B loads |
| [`outputs/run_log.md`](outputs/run_log.md) | Log of A's passes (visible logs) |
| [`outputs/blackboard.json`](outputs/blackboard.json) | Intermediate state, allows replaying passes |
| [`outputs/system_b_log.md`](outputs/system_b_log.md) | Trace of B's queries |

Format of each entity/relationship (excerpt — see [CLAUDE.md §4](CLAUDE.md)):

```json
{
  "id": "customer:medpharma", "type": "Customer", "name": "MedPharma",
  "layer": "operational",
  "attributes": { "priority_tier": "Platinum", "strategic_value": 1200000 },
  "sources": ["odoo.res_partner:C001", "sqlite.legacy_contacts:'Med Pharma SARL'"],
  "confidence": 0.95,
  "evidence": ["odoo name = 'MedPharma'", "legacy matched fuzzy 0.87"],
  "open_questions": []
}
```

---

## Limitations (hackathon state)

This is a **demo MVP**, not a production product. Assumed limitations:

- **Non-generic connectors.** Sources are wired through **mock MCP servers**
  ([`mcp_mocks/`](mcp_mocks/)) and file readers specific to the demo SMB's schema. There
  are **no generic connectors yet** (real Odoo, real Outlook, arbitrary TMS) — that's a
  planned upgrade behind the same interface, and the pipeline never depends on it.
- **Synthetic data.** The entire dataset is **generated** ([`data/`](data/), single source
  of truth [`data/canonical.py`](data/canonical.py)). Realistic and heterogeneous, but
  synthetic — no real company data.
- **Ontology frozen for the demo.** The published ontology is committed and static; the
  agentic pipeline works but we don't replay it for every demo (latency/cost).
- **Transport-specific schema.** The passes and heuristics (org chart reconstruction,
  shipment scoring) are calibrated for the demo transport SMB. Generalizing to other
  sectors remains to be done.
- **Latency.** System B takes ~35 s/answer (generation, not the tool turns). Output
  optimization is not done.
- **No action execution.** B *proposes* actions as text; it executes none. No auth, no
  deployment, no advanced graph database — out of MVP scope.

---

## What's next

Next steps beyond the MVP: **real connectors** (real Odoo/Outlook/TMS behind the MCP
interface), **ontology rebuilt on the fly** on real client data, **multi-sector**
generalization, B latency optimization, and the "vision" passes (governance/PII, business
glossary, metric definitions, human review).

---

## Repo structure

```
data/              # synthetic data + source of truth (canonical.py) + validate.py
mcp_mocks/         # 3 mock MCP servers (TMS Dashdoc / ERP Odoo / email)
system_a/          # System A — deterministic oracle (no LLM)
system_a_agents/   # System A — agentic extractor (Claude Agent SDK, passes p0→p7)
system_b/          # System B — conversational agent (NetworkX query tools)
ui/                # Flask server + canvas viz + chat wired to B
outputs/           # compiled ontologies + logs (committed, static)
CLAUDE.md          # reference technical spec
DATA_README.md     # data model documentation
```
