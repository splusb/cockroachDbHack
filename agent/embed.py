"""
Embedding module - converts symptom text into a 1536-dim vector using Amazon Bedrock Titan Embeddings V2.

Usage:
    from agent.embed import embed_symptoms
    vector = embed_symptoms("JWT validation failing, 401s spiking")
    # Returns: List[float] with 1536 dimensions
"""

import json
import time
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


def _get_bedrock_client():
    """Create a Bedrock Runtime client."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    return boto3.client("bedrock-runtime", **kwargs)


def embed_symptoms(symptoms: str) -> List[float]:
    """
    Convert a symptoms string into a 1536-dimensional embedding vector.

    Uses Amazon Bedrock Titan Text Embeddings V2.
    Retries up to 3 times with exponential backoff on throttling/timeout.

    Args:
        symptoms: The alert/symptom text to embed.

    Returns:
        List of 1536 floats representing the embedding vector.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    client = _get_bedrock_client()

    payload = json.dumps({
        "inputText": symptoms,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
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

            # Validate output shape
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(embedding)}"
                )

            return embedding

        except (client.exceptions.ThrottlingException, Exception) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF_SECONDS[attempt]
                time.sleep(backoff)
            continue

    raise RuntimeError(
        f"Failed to generate embedding after {MAX_RETRIES} attempts: {last_error}"
    )
