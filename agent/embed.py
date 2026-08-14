"""
Embedding module - converts symptom text into a 1024-dim vector.

Supports two modes:
- USE_LOCAL_EMBEDDING=True: Uses sentence-transformers locally (no AWS needed)
- USE_LOCAL_EMBEDDING=False: Uses Amazon Bedrock Titan Embeddings V2

Usage:
    from agent.embed import embed_symptoms
    vector = embed_symptoms("JWT validation failing, 401s spiking")
    # Returns: List[float] with 1024 dimensions
"""

import json
import time
import hashlib
import random
import boto3
from typing import List

from agent.config import (
    AWS_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    EMBEDDING_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
)

# ============================================================
# Set this to True to use local embeddings (no AWS needed)
# Set to False when Bedrock access is working
# ============================================================
USE_LOCAL_EMBEDDING = True


def _get_bedrock_client():
    """Create a Bedrock Runtime client."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    return boto3.client("bedrock-runtime", **kwargs)


def _local_embedding(text: str) -> List[float]:
    """
    Generate a deterministic embedding based on text content.

    Uses word-level hashing to produce vectors where similar texts
    have similar vectors (shared words shift the same dimensions).
    Good enough for demo and testing the full pipeline.
    """
    # Base vector from full text hash
    seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    embedding = [rng.gauss(0, 0.1) for _ in range(EMBEDDING_DIMENSIONS)]

    # Add word-level signal so similar texts produce similar vectors
    words = text.lower().split()
    for word in words:
        word_seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
        word_rng = random.Random(word_seed)
        for i in range(EMBEDDING_DIMENSIONS):
            embedding[i] += word_rng.gauss(0, 0.02)

    # Normalize to unit vector
    magnitude = sum(x * x for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


def embed_symptoms(symptoms: str) -> List[float]:
    """
    Convert a symptoms string into a 1024-dimensional embedding vector.

    Args:
        symptoms: The alert/symptom text to embed.

    Returns:
        List of 1024 floats representing the embedding vector.

    Raises:
        RuntimeError: If all retries are exhausted (Bedrock mode only).
    """
    if USE_LOCAL_EMBEDDING:
        return _local_embedding(symptoms)

    # Bedrock mode
    client = _get_bedrock_client()

    payload = json.dumps({
        "inputText": symptoms,
    })

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
            embedding = response_body["embedding"]

            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(embedding)}"
                )

            return embedding

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF_SECONDS[attempt]
                time.sleep(backoff)
            continue

    raise RuntimeError(
        f"Failed to generate embedding after {MAX_RETRIES} attempts: {last_error}"
    )
