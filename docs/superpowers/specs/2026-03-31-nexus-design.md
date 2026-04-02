# NEXUS - Self-Evolving Multi-Agent Operating System

**Version:** 0.1.0 (MVP)
**Date:** 2026-03-31
**Status:** Design

---

## 1. What Is NEXUS

NEXUS is an operating system metaphor for AI agents. Just like Linux manages processes, memory, and devices - NEXUS manages agents, shared memory, and tools (via MCP).

The killer feature: **agents that evolve themselves** by creating new MCP tools at runtime when they hit limitations. Not magic - an agent writes a Python function, a sandbox validates it, and it gets registered as an MCP server available to all agents.

### Core Metaphor

| OS Concept       | NEXUS Equivalent                    |
| ---------------- | ----------------------------------- |
| Process          | Agent (autonomous LLM-powered unit) |
| Kernel           | Kernel (lifecycle, scheduling, IPC) |
| Device Driver    | MCP Server (tool provider)          |
| RAM              | Shared Memory (vector + KV store)   |
| System Calls     | Agent API (spawn, kill, communicate)|
| Process Scheduler| Task Scheduler (priority routing)   |
| Shell            | CLI + Web Dashboard                 |

---

## 2. Architecture

### 2.1 Layer Diagram

```
+------------------------------------------------------------------+
|                      INTERFACE LAYER                              |
|  [ CLI ]  [ REST API (FastAPI) ]  [ WebSocket ]  [ Dashboard ]   |
+------------------------------------------------------------------+
         |                    |                  |
+------------------------------------------------------------------+
|                        KERNEL LAYER                               |
|  +-------------+  +------------+  +-----------+  +-------------+ |
|  | Agent       |  | Task       |  | Event     |  | Resource    | |
|  | Registry    |  | Scheduler  |  | Bus       |  | Manager     | |
|  +-------------+  +------------+  +-----------+  +-------------+ |
+------------------------------------------------------------------+
         |                    |                  |
+------------------------------------------------------------------+
|                        AGENT LAYER                                |
|  +---------------+  +-----------+  +------------+  +-----------+ |
|  | Orchestrator  |  | Researcher|  | Coder      |  | Analyst   | |
|  | (routes tasks)|  | (web/docs)|  | (code gen) |  | (data)    | |
|  +---------------+  +-----------+  +------------+  +-----------+ |
|  +---------------+                                               |
|  | Agent Factory | <- dynamically creates new agent types        |
|  +---------------+                                               |
+------------------------------------------------------------------+
         |                    |                  |
+------------------------------------------------------------------+
|                        TOOL LAYER (MCP)                           |
|  +-------------+  +---------------+  +-------------------------+ |
|  | MCP Server  |  | Dynamic Tool  |  | Built-in MCP Servers    | |
|  | Registry    |  | Creator       |  | (web, fs, code, shell)  | |
|  +-------------+  +-------+-------+  +-------------------------+ |
|                           |                                      |
|                    +------+------+                                |
|                    | Sandbox     | <- safe execution for new tools|
|                    +-------------+                                |
+------------------------------------------------------------------+
         |                    |                  |
+------------------------------------------------------------------+
|                       MEMORY LAYER                                |
|  +-------------+  +---------------+  +-------------------------+ |
|  | Short-term  |  | Long-term     |  | Shared State            | |
|  | (per agent  |  | (ChromaDB     |  | (KV store, accessible   | |
|  |  context)   |  |  vectors)     |  |  by all agents)         | |
|  +-------------+  +---------------+  +-------------------------+ |
+------------------------------------------------------------------+
```

### 2.2 Data Flow

```
User Request
    |
    v
[Kernel] -> receives request, creates Task
    |
    v
[Scheduler] -> assigns Task to Orchestrator Agent
    |
    v
[Orchestrator] -> analyzes task, creates execution plan
    |
    v
[Orchestrator spawns agents] -> researcher, coder, analyst as needed
    |
    +---> [Agent uses MCP tools] -> success -> results to shared memory
    |
    +---> [Agent needs tool that doesn't exist]
              |
              v
          [Agent proposes tool spec]
              |
              v
          [Coder Agent generates implementation]
              |
              v
          [Sandbox tests the tool]
              |
              v
          [Pass?] --yes--> [Register as MCP Server] -> available to ALL agents
              |
              no --> [Coder retries with error feedback, max 3 attempts]
    |
    v
[Agents communicate via Event Bus] -> share intermediate results
    |
    v
[Results aggregate in Shared Memory]
    |
    v
[Orchestrator synthesizes final response]
    |
    v
[Response to User via Interface Layer]
```

---

## 3. Component Design

### 3.1 Kernel

The kernel is the heart. It manages everything.

```python
# Conceptual API
class Kernel:
    registry: AgentRegistry       # tracks all agents
    scheduler: TaskScheduler      # routes tasks to agents
    event_bus: EventBus           # pub/sub for agent communication
    resource_mgr: ResourceManager # token budgets, rate limits

    async def boot() -> None                    # initialize kernel
    async def submit_task(task: Task) -> str     # submit work, returns task_id
    async def spawn_agent(spec: AgentSpec) -> Agent
    async def kill_agent(agent_id: str) -> None
    async def shutdown() -> None                 # graceful shutdown
```

**Agent Registry:**
- Stores agent metadata: id, type, status, capabilities, current task
- Lookup by capability (e.g., "find me an agent that can do web research")
- Tracks agent health (heartbeat, last activity)

**Task Scheduler:**
- Maintains a priority queue of tasks
- Routes tasks to the best available agent based on capabilities
- Handles task dependencies (task B waits for task A)
- Timeout and retry logic

**Event Bus:**
- Async pub/sub within the process
- Event types: `agent.spawned`, `agent.completed`, `tool.created`, `task.update`, `memory.write`
- Dashboard subscribes to all events via WebSocket
- All events are logged for replay/debugging

**Resource Manager:**
- Per-agent token budgets (prevent runaway costs)
- Global rate limiting per LLM provider
- Cost tracking (tokens used, estimated $)
- Circuit breaker: if an agent exceeds budget, pause and ask human

### 3.2 Agents

#### Base Agent

Every agent follows a lifecycle:

```
INIT -> IDLE -> RUNNING -> (PAUSED) -> COMPLETED / FAILED / TERMINATED
```

```python
# Conceptual API
class BaseAgent:
    id: str
    type: str
    status: AgentStatus
    capabilities: list[str]
    llm: LLMClient               # via litellm
    tools: list[MCPTool]         # available MCP tools
    memory: AgentMemory          # short-term context

    async def run(task: Task) -> TaskResult
    async def use_tool(tool_name: str, args: dict) -> Any
    async def communicate(target_agent_id: str, message: Message) -> None
    async def propose_tool(spec: ToolSpec) -> bool  # self-evolution
```

#### Pre-built Agents (MVP)

1. **Orchestrator Agent**
   - Role: Decomposes complex tasks into subtasks, spawns agents, aggregates results
   - Capabilities: planning, delegation, synthesis
   - Special: Only agent that can spawn/kill other agents
   - Has access to the Agent Registry to know what capabilities are available

2. **Researcher Agent**
   - Role: Web search, document retrieval, information gathering
   - MCP Tools: web_search, web_fetch, file_read
   - Capabilities: research, summarization, fact-checking

3. **Coder Agent**
   - Role: Code generation, code review, tool creation
   - MCP Tools: code_executor, file_write, file_read
   - Capabilities: python, javascript, code_review, tool_creation
   - Special: This is the agent that implements new tools during self-evolution

4. **Analyst Agent**
   - Role: Data analysis, reasoning over structured data
   - MCP Tools: code_executor (for pandas/analysis), file_read
   - Capabilities: data_analysis, visualization, statistical_reasoning

#### Agent Factory

Creates agents dynamically from a specification:

```python
spec = AgentSpec(
    type="custom",
    role="You are a security analysis expert...",
    capabilities=["security_audit", "vulnerability_scan"],
    tools=["code_executor", "file_read", "web_search"],
    model="claude-sonnet-4-6",
    token_budget=50000
)
agent = await kernel.spawn_agent(spec)
```

### 3.3 MCP Tool Layer

#### Built-in MCP Servers (MVP)

These ship with NEXUS:

1. **web_search** - Search the web via API (SerpAPI / Tavily)
2. **web_fetch** - Fetch and extract content from URLs
3. **file_system** - Read/write/list files in a sandboxed workspace
4. **code_executor** - Execute Python code in isolated subprocess
5. **shell** - Run shell commands (sandboxed, allowlisted)

Built-in servers run in-process as direct Python functions registered with MCP protocol schemas (no separate process overhead). External/dynamic tools use MCP stdio transport as separate processes.

#### Dynamic Tool Creator (Self-Evolution)

This is the differentiator. Flow:

```
1. Agent encounters a limitation
   Example: "I need to parse CSV data but no CSV tool exists"

2. Agent calls `propose_tool()` with a spec:
   {
     "name": "csv_parser",
     "description": "Parse CSV files and return structured data",
     "input_schema": {"file_path": "string", "delimiter": "string"},
     "output_schema": {"headers": ["string"], "rows": [["string"]]}
   }

3. Coder Agent receives the spec and generates Python implementation:
   - Function code
   - 3+ test cases
   - MCP server wrapper

4. Sandbox executes tests:
   - Isolated subprocess with timeout
   - No network access, limited filesystem
   - Memory limit

5. If ALL tests pass:
   - Tool registered in MCP Server Registry
   - Available to ALL agents immediately
   - Persisted to disk for future sessions

6. If tests fail:
   - Error fed back to Coder Agent
   - Retry up to 3 times
   - If all retries fail: log failure, agent falls back to manual approach
```

#### Tool Persistence

Created tools are saved to `~/.nexus/tools/` as:
```
tools/
  csv_parser/
    server.py        # MCP server implementation
    tool.py          # Core function
    tests.py         # Test cases
    manifest.json    # Metadata (name, schema, created_by, created_at)
```

On NEXUS boot, all persisted tools are loaded into the MCP registry.

### 3.4 Memory Layer

#### Short-term Memory (Per Agent)
- Conversation history for the current task
- Stored in-memory as a list of messages
- Cleared when agent completes task
- Max context window management (truncation/summarization)

#### Long-term Memory (Shared, Persistent)
- ChromaDB vector store
- Agents store useful findings: research results, code patterns, decisions
- Semantic search: agents can query "what do we know about X?"
- Namespaced by project/session

#### Shared State (Real-time KV)
- In-memory dict (v1), Redis-backed (v2)
- Agents read/write key-value pairs
- Use case: orchestrator stores the execution plan, agents read their assignments
- No locking needed for v1 (single-process asyncio = cooperative multitasking, no true concurrency)
- Events emitted on every write (dashboard picks these up)

### 3.5 Interface Layer

#### CLI
```bash
# Boot NEXUS
nexus start

# Submit a task
nexus run "Research the top 5 MCP servers and create a comparison report"

# Interactive mode
nexus shell

# List running agents
nexus agents list

# View created tools
nexus tools list

# Dashboard
nexus dashboard  # opens browser to localhost:3000
```

#### REST API (FastAPI)
```
POST   /api/tasks              # submit task
GET    /api/tasks/{id}         # task status + result
GET    /api/agents             # list active agents
POST   /api/agents             # spawn agent manually
DELETE /api/agents/{id}        # kill agent
GET    /api/tools              # list all MCP tools
GET    /api/memory/{key}       # read shared memory
WS     /api/ws/events          # real-time event stream
```

#### Web Dashboard (Next.js)

**Pages:**

1. **Dashboard Home** - Live view of NEXUS state
   - Active agents (cards with status, current task, token usage)
   - Task queue (pending, in-progress, completed)
   - Recent events timeline
   - System metrics (total tokens, cost, agents spawned)

2. **Agent Graph** - Real-time visualization
   - Nodes = agents, edges = communication
   - Animated data flow between agents
   - Click agent to see its reasoning trace
   - Watch agents spawn/die in real-time

3. **Task Detail** - Deep dive into a task
   - Execution plan (from orchestrator)
   - Agent assignments
   - Step-by-step reasoning traces
   - Tool calls with inputs/outputs
   - Timeline view

4. **Tool Registry** - All MCP tools
   - Built-in vs. agent-created
   - Usage stats
   - Test results for created tools
   - Tool creation history

5. **Memory Explorer** - Browse shared memory
   - KV store viewer
   - Vector memory search
   - Memory timeline (who wrote what, when)

---

## 4. Tech Stack

### Backend (Python)

| Dependency        | Purpose                      | Why This One               |
| ----------------- | ---------------------------- | -------------------------- |
| `python 3.11+`   | Runtime                      | Async, typing, performance |
| `mcp`             | MCP protocol SDK             | Official Anthropic SDK     |
| `litellm`         | Universal LLM interface      | Claude, OpenAI, Gemini, local - one API |
| `chromadb`        | Vector store                 | Zero-config, embedded, good enough for v1 |
| `fastapi`         | REST API + WebSocket         | Async, fast, auto-docs    |
| `uvicorn`         | ASGI server                  | Standard for FastAPI       |
| `pydantic`        | Data models + validation     | Type safety, serialization |
| `aiosqlite`       | Persistent state             | Async SQLite, zero-config  |
| `rich`            | CLI output                   | Beautiful terminal UI      |
| `typer`           | CLI framework                | Clean CLI with type hints  |
| `python-dotenv`   | Config                       | .env file loading          |

### Dashboard (TypeScript)

| Dependency        | Purpose                      | Why This One               |
| ----------------- | ---------------------------- | -------------------------- |
| `next.js 14+`    | React framework              | App Router, SSR, fast      |
| `typescript`      | Type safety                  | Non-negotiable             |
| `tailwind css`    | Styling                      | Utility-first, fast dev    |
| `shadcn/ui`       | UI components                | Beautiful, accessible, customizable |
| `reactflow`       | Agent graph visualization    | Purpose-built for node graphs |
| `socket.io`       | Real-time events             | Reliable WebSocket wrapper |
| `recharts`        | Charts/metrics               | Simple, React-native       |
| `framer-motion`   | Animations                   | Agent spawn/die animations |

### Infrastructure (v1 - Local Only)

- No Docker, no Kubernetes, no cloud services for v1
- Everything runs locally: `nexus start` boots the full system
- SQLite for persistence, ChromaDB embedded, in-process event bus
- Dashboard dev server via Next.js

---

## 5. Project Structure

```
nexus/
├── nexus/                         # Core Python package
│   ├── __init__.py
│   ├── main.py                    # Entry point, boots kernel
│   ├── config.py                  # Configuration (pydantic settings)
│   │
│   ├── kernel/                    # OS Kernel
│   │   ├── __init__.py
│   │   ├── kernel.py              # Main kernel class
│   │   ├── registry.py            # Agent registry
│   │   ├── scheduler.py           # Task scheduler + queue
│   │   └── resource.py            # Token budgets, rate limits
│   │
│   ├── agents/                    # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent abstract class
│   │   ├── factory.py             # Dynamic agent creation
│   │   ├── orchestrator.py        # Task decomposition + delegation
│   │   ├── researcher.py          # Web research agent
│   │   ├── coder.py               # Code generation + tool creation
│   │   └── analyst.py             # Data analysis agent
│   │
│   ├── mcp_layer/                 # MCP tool management
│   │   ├── __init__.py
│   │   ├── registry.py            # MCP server registry
│   │   ├── creator.py             # Dynamic tool creator
│   │   ├── sandbox.py             # Safe execution sandbox
│   │   └── servers/               # Built-in MCP servers
│   │       ├── __init__.py
│   │       ├── web_search.py      # Web search server
│   │       ├── web_fetch.py       # URL content fetcher
│   │       ├── file_system.py     # File operations
│   │       └── code_executor.py   # Python code execution
│   │
│   ├── memory/                    # Memory subsystem
│   │   ├── __init__.py
│   │   ├── short_term.py          # Per-agent conversation memory
│   │   ├── long_term.py           # ChromaDB vector store
│   │   └── shared.py              # Shared KV state
│   │
│   ├── events/                    # Event system
│   │   ├── __init__.py
│   │   ├── bus.py                 # Async event bus
│   │   └── types.py               # Event type definitions
│   │
│   ├── api/                       # REST API + WebSocket
│   │   ├── __init__.py
│   │   ├── server.py              # FastAPI app
│   │   ├── routes/
│   │   │   ├── tasks.py
│   │   │   ├── agents.py
│   │   │   ├── tools.py
│   │   │   └── memory.py
│   │   └── websocket.py           # WebSocket event streaming
│   │
│   └── cli/                       # CLI interface
│       ├── __init__.py
│       └── app.py                 # Typer CLI commands
│
├── dashboard/                     # Next.js web dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         # Root layout
│   │   │   ├── page.tsx           # Dashboard home
│   │   │   ├── agents/
│   │   │   │   └── page.tsx       # Agent graph view
│   │   │   ├── tasks/
│   │   │   │   ├── page.tsx       # Task list
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx   # Task detail
│   │   │   ├── tools/
│   │   │   │   └── page.tsx       # Tool registry
│   │   │   └── memory/
│   │   │       └── page.tsx       # Memory explorer
│   │   ├── components/
│   │   │   ├── agent-card.tsx
│   │   │   ├── agent-graph.tsx    # ReactFlow graph
│   │   │   ├── event-timeline.tsx
│   │   │   ├── task-card.tsx
│   │   │   ├── metrics-bar.tsx
│   │   │   └── tool-card.tsx
│   │   ├── lib/
│   │   │   ├── api.ts             # API client
│   │   │   ├── socket.ts          # WebSocket client
│   │   │   └── types.ts           # TypeScript types
│   │   └── hooks/
│   │       ├── use-events.ts      # Real-time event hook
│   │       └── use-agents.ts      # Agent state hook
│   └── public/
│
├── tests/                         # Test suite
│   ├── test_kernel.py
│   ├── test_agents.py
│   ├── test_mcp.py
│   ├── test_memory.py
│   └── test_scheduler.py
│
├── examples/                      # Example usage
│   ├── basic_task.py              # Simple single-agent task
│   ├── multi_agent.py             # Multi-agent collaboration
│   └── self_evolve.py             # Tool creation demo
│
├── pyproject.toml                 # Python package config
├── .env.example                   # Environment variables template
├── .gitignore
└── README.md
```

---

## 6. Key Interfaces (Pydantic Models)

```python
# ---- Task ----
class Task:
    id: str                        # uuid
    description: str               # what to do
    priority: int                  # 1-10
    status: TaskStatus             # pending | assigned | running | completed | failed
    assigned_to: str | None        # agent_id
    parent_task_id: str | None     # for subtasks
    result: Any | None
    created_at: datetime
    completed_at: datetime | None
    token_budget: int              # max tokens for this task

class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# ---- Agent ----
class AgentSpec:
    type: str                      # orchestrator | researcher | coder | analyst | custom
    role: str                      # system prompt / role description
    capabilities: list[str]        # what this agent can do
    tools: list[str]               # MCP tool names
    model: str                     # LLM model identifier
    token_budget: int              # max tokens per task

class AgentStatus(str, Enum):
    INIT = "init"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"

# ---- MCP Tool ----
class ToolSpec:
    name: str
    description: str
    input_schema: dict             # JSON Schema
    output_schema: dict            # JSON Schema
    proposed_by: str               # agent_id that proposed it

class RegisteredTool:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    server_path: str               # path to MCP server file
    is_builtin: bool               # built-in vs agent-created
    created_by: str | None         # agent_id (None for built-in)
    created_at: datetime
    usage_count: int
    test_results: list[TestResult]

# ---- Events ----
class NexusEvent:
    id: str
    type: str                      # e.g., "agent.spawned", "tool.created"
    source: str                    # agent_id or "kernel"
    data: dict                     # event-specific payload
    timestamp: datetime

# Event types:
# agent.spawned, agent.status_changed, agent.completed, agent.failed, agent.terminated
# task.created, task.assigned, task.completed, task.failed
# tool.proposed, tool.testing, tool.created, tool.failed
# memory.write, memory.read
# kernel.boot, kernel.shutdown

# ---- Messages (IPC) ----
class AgentMessage:
    from_agent: str
    to_agent: str
    content: str
    message_type: str              # request | response | broadcast
    correlation_id: str | None     # for request-response pairing
    timestamp: datetime
```

---

## 7. Human-in-the-Loop

Certain actions require human approval:

| Action                      | Approval Required | Why                          |
| --------------------------- | ----------------- | ---------------------------- |
| Spawn new agent             | No                | Orchestrator decides         |
| Use built-in MCP tool       | No                | Pre-approved                 |
| Create new MCP tool         | **Yes**           | Executing generated code     |
| Exceed token budget         | **Yes**           | Cost control                 |
| Write to filesystem         | Configurable      | Safety                       |
| Execute shell commands       | **Yes**           | Security                     |
| Access external APIs        | Configurable      | Depends on API               |

Implementation: When approval is needed, the kernel emits an `approval.requested` event. The CLI/Dashboard shows a prompt. Agent is paused until approved/rejected.

---

## 8. Implementation Phases

### Phase 1: Foundation (Core kernel + basic agents)
- Kernel: boot, shutdown, agent lifecycle
- Event bus (in-memory async)
- Base agent with LLM integration (litellm)
- Orchestrator agent (task decomposition)
- 1 worker agent (Researcher with web_search tool)
- Shared memory (in-memory KV)
- CLI: `nexus start`, `nexus run`, `nexus shell`
- Basic logging

**Deliverable:** Submit a task via CLI, orchestrator decomposes it, researcher executes, result returned.

### Phase 2: Multi-Agent + MCP (Full agent roster + tool system)
- Coder agent + Analyst agent
- Built-in MCP servers (web_search, file_system, code_executor)
- MCP Server Registry
- Agent-to-agent communication via event bus
- Task scheduler with priority queue
- Resource manager (token budgets)
- ChromaDB long-term memory

**Deliverable:** Multi-agent collaboration on complex tasks. Agents communicate and share results.

### Phase 3: Self-Evolution (Dynamic tool creation)
- Dynamic Tool Creator
- Sandbox for safe tool testing
- Tool persistence to disk
- Coder agent generates + tests new tools
- Human approval flow for tool creation
- Tool auto-loading on boot

**Deliverable:** Agent encounters limitation, creates new tool, tool available to all agents.

### Phase 4: Dashboard (Real-time visualization)
- Next.js dashboard scaffold
- WebSocket event streaming from backend
- Dashboard home (agents, tasks, metrics)
- Agent graph visualization (ReactFlow)
- Task detail with reasoning traces
- Tool registry viewer
- Memory explorer

**Deliverable:** Full visual dashboard showing NEXUS running in real-time.

### Phase 5: Polish + Open Source (GitHub-ready)
- README with architecture diagrams, GIFs, quickstart
- Examples directory with demo scripts
- Comprehensive tests
- CI/CD (GitHub Actions)
- PyPI package (`pip install nexus-agents`)
- Docker compose for one-command demo
- Documentation site

**Deliverable:** Professional open-source project ready for GitHub viral moment.

---

## 9. Security Boundaries

- **Code execution sandbox:** All generated code runs in isolated subprocess with:
  - Timeout (30s default)
  - Memory limit (256MB)
  - No network access (for tool creation)
  - Restricted filesystem access (only workspace dir)
  - No subprocess spawning

- **MCP tool isolation:** Built-in tools run in-process (direct function calls wrapped in MCP protocol). Agent-created tools run as separate subprocess MCP servers (stdio transport) for isolation.
- **Token budgets:** Hard limits per agent and per task
- **Human approval:** Required for high-risk actions (see Section 7)
- **No secrets in memory:** API keys never stored in shared memory, only in .env

---

## 10. Configuration

```env
# .env.example

# LLM Providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Default model (litellm format)
NEXUS_DEFAULT_MODEL=claude-sonnet-4-6

# Resource limits
NEXUS_MAX_AGENTS=10
NEXUS_TOKEN_BUDGET_PER_TASK=100000
NEXUS_TOOL_CREATION_TIMEOUT=30

# Web search (for researcher agent)
TAVILY_API_KEY=tvly-...

# Dashboard
NEXUS_DASHBOARD_PORT=3000
NEXUS_API_PORT=8000

# Human approval
NEXUS_REQUIRE_APPROVAL_FOR_TOOLS=true
NEXUS_REQUIRE_APPROVAL_FOR_SHELL=true
```

---

## 11. What Makes This GitHub-Viral

1. **Novel concept:** "Agents that build their own tools" - hasn't been done well
2. **Visual demo:** Real-time dashboard showing agents spawning, communicating, creating tools
3. **OS metaphor:** Instantly understandable framing for complex multi-agent systems
4. **Actually useful:** Not a toy - handles real multi-step tasks
5. **MCP-native:** Rides the MCP wave, interoperable with MCP ecosystem
6. **Great DX:** `pip install nexus-agents && nexus start` - running in 60 seconds
7. **Extensible:** Custom agents and tools via simple Python classes

---

## 12. Non-Goals (v1)

- Distributed multi-node execution
- Persistent agent processes (agents are task-scoped)
- Custom LLM training/fine-tuning
- Mobile interface
- Authentication/multi-user
- Cloud deployment platform
- Billing/metering
