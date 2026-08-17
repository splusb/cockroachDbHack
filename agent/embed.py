"""
Embedding module - converts text into vectors using OpenAI or Bedrock.

Usage:
    from agent.embed import embed_symptoms
    vector = embed_symptoms("JWT validation failing, 401s spiking")
    # Returns: List[float] with 1536 dimensions
"""

import json
import time
import boto3
from typing import List
from openai import OpenAI

from agent.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    AWS_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    EMBEDDING_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
)


def embed_symptoms(symptoms: str) -> List[float]:
    """
    Convert a symptoms string into an embedding vector.

    Uses OpenAI (default) or Bedrock depending on LLM_PROVIDER config.

    Args:
        symptoms: The alert/symptom text to embed.

    Returns:
        List of floats representing the embedding vector.
    """
    if LLM_PROVIDER == "openai":
        return _embed_openai(symptoms)
    else:
        return _embed_bedrock(symptoms)


def _embed_openai(text: str) -> List[float]:
    """Generate embedding using OpenAI API."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL,
                input=text,
            )
            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS[attempt])
            continue

    raise RuntimeError(f"OpenAI embedding failed after {MAX_RETRIES} attempts: {last_error}")


def _embed_bedrock(text: str) -> List[float]:
    """Generate embedding using Bedrock Titan."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    client = boto3.client("bedrock-runtime", **kwargs)

    payload = json.dumps({"inputText": text})

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.invoke_model(
                modelId=EMBEDDING_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=payload,
            )
            response_body = json.loads(response["body"].read())
            return response_body["embedding"]
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS[attempt])
            continue

    raise RuntimeError(f"Bedrock embedding failed after {MAX_RETRIES} attempts: {last_error}")
