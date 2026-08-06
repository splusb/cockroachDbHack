"""
Configuration loader for the Incident Memory Agent.
Reads .env file and exposes all settings as module-level constants.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# CockroachDB
COCKROACHDB_URL = os.getenv("COCKROACHDB_URL", "")

# AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# Bedrock model IDs
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

# MCP Server
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

# Optional
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Vector search settings
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
EMBEDDING_DIMENSIONS = 1536

# Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [0.5, 1.0, 2.0]
