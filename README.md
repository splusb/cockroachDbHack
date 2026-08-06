# Incident Memory Agent

> An agentic incident-response tool that learns from every investigation — powered by CockroachDB vector search and Amazon Bedrock.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Architecture

```
Alert Source (API Gateway POST)
        │
        ▼
  AWS Lambda Handler
        │
        ▼
  Agent Pipeline
  ┌─────────────────────────────────┐
  │ embed.py    → Bedrock Titan v2  │
  │ retrieve.py → MCP Server search │
  │ reason.py   → Bedrock LLM      │
  │ writeback.py→ MCP Server INSERT │
  └─────────────────────────────────┘
        │
        ▼
  CockroachDB Cloud
  (Vector Index + MCP Server)
```

## CockroachDB Tools Used

- **Distributed Vector Indexing** — semantic search over incident embeddings
- **Cloud Managed MCP Server** — agent's programmatic interface to the cluster

## AWS Services Used

- **Amazon Bedrock** — Titan Embeddings v2 + Claude 3.5 Sonnet for reasoning
- **AWS Lambda** — serverless execution triggered by API Gateway

## Setup

_See CLAUDE.md for detailed build steps._

## License

MIT
