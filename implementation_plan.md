# NEXUS Phase 1: Foundation Build

## Goal
Build the working foundation: kernel → agents → tools → memory → interface. By the end, a user can `nexus run "research X"` and get a real result through orchestrator → researcher flow.

## Build Order (dependency-first)

### 1. Project Scaffolding
- `pyproject.toml` — package config with all Phase 1 deps
- `nexus/config.py` — Pydantic Settings (env vars)
- `.env.example`
- `.gitignore`

### 2. Events Layer (`nexus/events/`)
- `types.py` — `NexusEvent` model, all event type constants
- `bus.py` — async pub/sub EventBus (in-memory, asyncio.Queue per subscriber)

### 3. Memory Layer (`nexus/memory/`)
- `short_term.py` — per-agent message list with max-length truncation
- `shared.py` — in-memory KV store with event emission on writes

### 4. MCP Tool Layer (`nexus/mcp_layer/`)
- `registry.py` — ToolRegistry (register/lookup/list tools)
- `servers/web_search.py` — built-in web search (Tavily API)
- `servers/file_system.py` — sandboxed file read/write/list
- `servers/code_executor.py` — subprocess Python execution with timeout

### 5. Kernel (`nexus/kernel/`)
- `registry.py` — AgentRegistry (CRUD agents, lookup by capability)
- `scheduler.py` — priority queue, task assignment, timeout/retry
- `resource.py` — per-agent token budget tracking, rate limiter
- `kernel.py` — main Kernel class (boot, shutdown, submit_task, spawn_agent, kill_agent)

### 6. Agents (`nexus/agents/`)
- `base.py` — BaseAgent ABC (lifecycle, run loop, tool use, LLM calls via litellm)
- `orchestrator.py` — decomposes tasks, spawns sub-agents, aggregates
- `researcher.py` — web search + summarization agent

### 7. API (`nexus/api/`)
- `server.py` — FastAPI app with lifespan (boots kernel)
- `routes/tasks.py` — POST/GET tasks
- `routes/agents.py` — GET/POST/DELETE agents
- `routes/tools.py` — GET tools
- `websocket.py` — event stream over WS

### 8. CLI (`nexus/cli/`)
- `app.py` — `nexus start`, `nexus run`, `nexus shell`, `nexus agents list`, `nexus tools list`

### 9. Entry Point
- `nexus/main.py` — boots kernel, starts API server

## Key Design Decisions

- **No MCP subprocess for built-in tools.** Built-in tools are direct async Python functions registered with MCP-compatible schemas. Only dynamic (Phase 3) tools use subprocess isolation.
- **Event bus is in-process asyncio.** No Redis/external broker for v1.
- **litellm for all LLM calls.** Single interface regardless of provider.
- **No locking on shared KV.** Single-process asyncio = cooperative multitasking.

## Verification

- `nexus start` boots without errors
- `nexus run "What is MCP?"` → orchestrator decomposes → researcher searches → result returned
- `nexus agents list` shows active agents
- `nexus tools list` shows built-in tools
- FastAPI docs at `localhost:8000/docs`
- WebSocket events stream to connected clients
