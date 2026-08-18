"""
Configuration loader for the Incident Memory Agent.
Reads .env file and exposes all settings as module-level constants.
"""

import os
from pathlib import Path

# Only load .env if the file exists (won't exist in Lambda)
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path, override=False)

# CockroachDB
COCKROACHDB_URL = os.getenv("COCKROACHDB_URL", "postgresql://root@localhost:26257/defaultdb?sslmode=disable")

# LLM Provider: "openai" or "bedrock"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

# AWS (fallback when LLM_PROVIDER=bedrock)
AWS_REGION = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-west-2"))
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# Bedrock model IDs
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")

# MCP Server
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

# Vector search settings
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
EMBEDDING_DIMENSIONS = 1536  # OpenAI text-embedding-3-small = 1536

# Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [0.5, 1.0, 2.0]

# Self-healing: path to the buggy app code the agent can modify
BUGGY_APP_PATH = os.getenv("BUGGY_APP_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo-app"
))
