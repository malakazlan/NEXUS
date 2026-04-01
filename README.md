# NEXUS — Self-Evolving Multi-Agent Operating System

An OS for AI agents. Agents that build their own tools.

## Quick Start

```bash
# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Start the API server
nexus start

# Run a task directly
nexus run "Research the top 5 MCP servers and create a comparison report"

# Interactive shell
nexus shell

# List agents (while server is running)
nexus agents list

# List tools
nexus tools list
```

## Architecture

```
Interface  →  CLI | REST API | WebSocket | Dashboard
Kernel     →  Agent Registry | Task Scheduler | Event Bus | Resource Manager
Agents     →  Orchestrator | Researcher | Coder | Analyst | Dynamic Factory
Tools      →  MCP Registry | Built-in Servers | Dynamic Tool Creator
Memory     →  Short-term (per agent) | Long-term (ChromaDB) | Shared KV
```

## API

```
POST   /api/tasks              Submit a task
GET    /api/tasks/{id}         Task status + result
GET    /api/agents             List active agents
POST   /api/agents             Spawn agent
DELETE /api/agents/{id}        Kill agent
GET    /api/tools              List MCP tools
GET    /api/memory/{key}       Read shared memory
WS     /api/ws/events          Real-time event stream
GET    /api/health             Health check
```

## Project Structure

```
nexus/
├── kernel/          # Agent lifecycle, scheduling, resources
├── agents/          # Orchestrator, Researcher, Coder, Analyst, Factory
├── mcp_layer/       # MCP tool registry + built-in servers
├── memory/          # Short-term, long-term (ChromaDB), shared KV
├── events/          # Async event bus
├── api/             # FastAPI REST + WebSocket
└── cli/             # Typer CLI
```
