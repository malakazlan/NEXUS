# NEXUS — Self-Evolving Multi-Agent OS

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
  <img src="https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square" />
  <img src="https://img.shields.io/badge/protocol-MCP-black?style=flat-square" />
  <img src="https://img.shields.io/badge/memory-ChromaDB-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/dashboard-Next.js-black?style=flat-square" />
</p>

<p align="center">
  An operating system for AI agents — where agents can <strong>create their own tools at runtime</strong>.
</p>

---

## What is NEXUS?

NEXUS is a multi-agent runtime that treats AI agents like OS processes. It provides a kernel that manages agent lifecycles, a shared memory system, an event bus for IPC, and a self-evolution engine — where agents detect missing capabilities and generate new MCP tools on the fly, complete with code, tests, and human approval.

**The killer feature:** an agent realizes it needs a capability it doesn't have → asks the CoderAgent to write it → sandbox validates it with pytest → you approve it → it's live as an MCP tool for every agent in the system. No restart. No redeploy.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Interface Layer   CLI · REST API · WebSocket · Dashboard │
├─────────────────────────────────────────────────────────┤
│  Kernel            Agent Registry · Task Scheduler        │
│                    Event Bus · Resource Manager           │
├─────────────────────────────────────────────────────────┤
│  Agent Layer       Orchestrator · Researcher · Coder      │
│                    Analyst · Dynamic Factory              │
├─────────────────────────────────────────────────────────┤
│  Tool Layer (MCP)  Registry · Built-in Servers            │
│                    Sandbox · DynamicToolCreator           │
├─────────────────────────────────────────────────────────┤
│  Memory Layer      Short-term · Long-term (ChromaDB)      │
│                    Shared KV · Agent IPC                  │
└─────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Description |
|---|---|
| **Self-Evolution** | Agents generate new MCP tools at runtime — code + tests + approval |
| **Multi-Agent IPC** | Agents communicate over an async event bus with full message routing |
| **Long-term Memory** | ChromaDB vector store — semantic search across all agent knowledge |
| **Human-in-the-Loop** | Approval gate for tool creation — asyncio.Future based, non-blocking |
| **Sandbox Testing** | All generated code runs in isolated subprocess with timeout before going live |
| **Task Scheduling** | Priority queue (1–10) with subtask support and token budget tracking |
| **5 Agent Types** | Orchestrator, Researcher, Coder, Analyst, Dynamic (runtime-created) |
| **4 Built-in MCP Tools** | web_search, web_fetch, file_system, code_executor |
| **REST + WebSocket API** | Full FastAPI backend with real-time event streaming |
| **React Dashboard** | Live monitoring UI — agents, tasks, tools, events, memory explorer |

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/malakazlan/NEXUS.git
cd NEXUS
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

```env
# .env
LITELLM_API_KEY=sk-...          # OpenAI / Anthropic / any provider
TAVILY_API_KEY=tvly-...         # For web_search tool (optional)
NEXUS_DEFAULT_MODEL=gpt-4o-mini
NEXUS_REQUIRE_APPROVAL_FOR_TOOLS=true
```

### 3. Start the backend

```bash
nexus start
# API running at http://localhost:8000
# Docs at      http://localhost:8000/docs
```

### 4. Start the dashboard

```bash
cd dashboard
npm install
npm run dev
# Dashboard at http://localhost:3000
```

### 5. Run a task

```bash
# CLI
nexus run "Research the top 5 MCP servers and write a comparison report"

# Or via API
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Summarize the latest AI news", "priority": 3}'
```

---

## Self-Evolution in Action

This is the core loop that makes NEXUS different:

```python
# An agent detects it needs a capability it doesn't have
await agent.propose_tool(
    name="sentiment_analyzer",
    description="Analyze sentiment of text and return a score from -1 to 1",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"]
    }
)

# NEXUS then:
# 1. CoderAgent generates Python async function + pytest test suite via LLM
# 2. Sandbox runs tests in isolated subprocess — must pass to continue
# 3. ApprovalGate notifies you (CLI or dashboard) and waits for your OK
# 4. Tool is persisted to ~/.nexus/tools/ and registered as a live MCP tool
# 5. All agents can now call sentiment_analyzer — survives kernel restarts
```

---

## REST API

```
POST   /api/tasks              Submit a task
POST   /api/tasks/async        Fire-and-forget task
GET    /api/tasks              List all tasks (filter by ?status=)
GET    /api/tasks/{id}         Task status + result

GET    /api/agents             List active agents
POST   /api/agents             Spawn an agent
DELETE /api/agents/{id}        Terminate an agent

GET    /api/tools              List all MCP tools (built-in + dynamic)
POST   /api/tools              Create a dynamic tool manually

GET    /api/memory             List shared memory keys
GET    /api/memory/{key}       Read a value
POST   /api/memory             Write a value

GET    /api/events             Recent events (last 50)
WS     /api/ws/events          Real-time event stream

GET    /api/health             System health
```

Interactive docs: `http://localhost:8000/docs`

---

## Project Structure

```
NEXUS/
├── nexus/
│   ├── kernel/
│   │   ├── kernel.py          # Boot, shutdown, agent/task lifecycle
│   │   ├── registry.py        # Agent registry
│   │   ├── scheduler.py       # Priority task queue
│   │   └── resource.py        # Token budget tracking
│   ├── agents/
│   │   ├── base.py            # BaseAgent — LLM calls, tool use, IPC
│   │   ├── orchestrator.py    # Task decomposition + delegation
│   │   ├── researcher.py      # Web search + analysis
│   │   ├── coder.py           # Code generation + tool creation
│   │   ├── analyst.py         # Data analysis
│   │   ├── factory.py         # Dynamic agent creation at runtime
│   │   └── messaging.py       # Agent-to-agent message router
│   ├── mcp_layer/
│   │   ├── registry.py        # MCP tool registry
│   │   ├── creator.py         # DynamicToolCreator — self-evolution engine
│   │   ├── sandbox.py         # Subprocess sandbox for testing generated code
│   │   └── servers/           # Built-in MCP tools
│   │       ├── web_search.py
│   │       ├── web_fetch.py
│   │       ├── file_system.py
│   │       └── code_executor.py
│   ├── memory/
│   │   ├── short_term.py      # Per-agent conversation memory
│   │   ├── long_term.py       # ChromaDB vector store
│   │   └── shared.py          # Cross-agent KV store
│   ├── events/
│   │   ├── bus.py             # Async pub/sub event bus
│   │   ├── types.py           # 20+ event types
│   │   └── approval.py        # Human-in-the-loop approval gate
│   ├── api/
│   │   ├── server.py          # FastAPI app + CORS + lifespan
│   │   ├── websocket.py       # Real-time event broadcaster
│   │   └── routes/            # tasks, agents, tools, memory
│   └── cli/
│       └── app.py             # Typer CLI — start, run, shell, list
├── dashboard/                 # Next.js 14 monitoring dashboard
│   ├── app/                   # Pages: overview, agents, tasks, tools, events, memory
│   ├── components/            # UI component library
│   └── lib/                   # API client, WebSocket hook, types
├── tests/
│   ├── test_boot.py
│   ├── test_messaging.py
│   ├── test_long_term_memory.py
│   ├── test_sandbox.py
│   ├── test_tool_creator.py
│   └── test_self_evolution_e2e.py
└── pyproject.toml
```

---

## Running Tests

```bash
pytest tests/ -v
```

All 20 tests cover: kernel boot, agent IPC, ChromaDB memory, sandbox isolation, tool creation, and the full self-evolution end-to-end lifecycle.

---

## Dashboard

The dashboard connects to the NEXUS backend at `localhost:8000` and provides:

- **Overview** — live metrics, event activity chart, agent and task summaries
- **Agents** — spawn/terminate agents, view model, token usage, capabilities
- **Tasks** — priority queue, expandable results and errors, real-time status
- **Tools** — built-in and self-created MCP tools, create tools manually
- **Events** — terminal-style live stream with category filtering and JSON inspection
- **Memory** — browse and write to the shared agent KV store

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM interface | [litellm](https://github.com/BerriAI/litellm) — works with any provider |
| API | FastAPI + Uvicorn |
| Vector memory | ChromaDB |
| CLI | Typer + Rich |
| Dashboard | Next.js 14, Tailwind CSS, Recharts, SWR |
| Tests | pytest-asyncio |
| Python | 3.10+ |

---

## License

MIT
