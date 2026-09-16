---
noteId: "4b0df350b1d211f1a1d40b869ec09816"
tags: []

---

# Project Structure

This layout adapts the supplied RAG example to a general research agent. It
keeps the same separation of concerns without adding ingestion, chunking,
embeddings, or a vector database before the project needs them.

```text
ai-agent-course/
|-- apps/                         # Streamlit and future clients
|-- src/first_agent/
|   |-- agents/                   # Agent facades and dependency composition
|   |-- workflows/                # LangGraph state, nodes, edges, and routing
|   |-- memory/                   # Short-term checkpoints and long-term stores
|   |-- skills/                   # Reusable reasoning and synthesis behaviors
|   |-- tools/                    # Search, scraping, and future tool adapters
|   |-- models/                   # Provider-neutral model interfaces/adapters
|   |-- prompts/                  # Prompt construction
|   |-- config/                   # Application defaults
|   `-- agent.py                  # Compatibility import
|-- tests/                        # Unit and workflow tests
|-- docs/                         # Architecture and operations guides
|-- logs/                         # Runtime diagnostics
|-- assets/                       # Documents and static assets
|-- mcp/                          # Future streamable HTTP MCP servers/setup
|-- skills/                       # Future distributable skill packages
|-- tools/                        # Future standalone developer utilities
|-- first_agent.py                # CLI entry point
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Memory Boundaries

Short-term memory is workflow state for one `thread_id`. The local
`InMemorySaver` supports development and tests, but restarts erase it and
multiple server processes do not share it.

Long-term memory is explicit, namespaced information worth reusing across
threads, such as a saved topic or user-approved preference. The current
in-memory implementation establishes the contract only. Production should use
a durable LangGraph-compatible store or database and define consent, deletion,
retention, and tenant-isolation policies.

## Extension Rules

- Add a new capability to `skills/` when it describes reusable agent behavior.
- Add deterministic external actions or data access to `tools/`.
- Add branching, retries, or multi-step state transitions to `workflows/`.
- Add provider SDK details only to `models/`.
- Add FastAPI as a transport layer; it should call agent facades rather than
  duplicating orchestration.
- Add RAG-specific ingestion and retrieval folders only when document-backed
  retrieval becomes an actual requirement.
