"""
Reasoning module - uses Amazon Bedrock LLM to analyze an incident
based on similar past incidents and propose a root cause + fix.

Usage:
    from agent.reason import reason_incident
    result = reason_incident(service, symptoms, similar_incidents)
    # Returns: dict with root_cause, fix, confidence, reasoning
"""

import json
import time
import boto3
from typing import List, Dict, Any

from agent.config import (
    AWS_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    LLM_MODEL_ID,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
)


SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) investigating a production incident.

Given a current alert and similar past incidents from memory, analyze the situation and propose:
1. The most likely root cause
2. A specific fix/remediation step
3. Your confidence level (high, medium, low)
4. Brief reasoning explaining your analysis

You MUST respond with valid JSON in exactly this format:
{
  "root_cause": "concise description of the root cause",
  "fix": "specific actionable remediation step",
  "confidence": "high|medium|low",
  "reasoning": "brief explanation of how you reached this conclusion"
}

If no similar incidents are available, reason from first principles based on the service and symptoms."""


def _get_bedrock_client():
    """Create a Bedrock Runtime client."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    return boto3.client("bedrock-runtime", **kwargs)


def _build_user_prompt(
    service: str, symptoms: str, similar_incidents: List[Dict[str, Any]]
) -> str:
    """Build the user prompt with the current alert and similar incidents context."""
    prompt = f"""## Current Alert
- **Service:** {service}
- **Symptoms:** {symptoms}

## Similar Past Incidents from Memory
"""
    if similar_incidents:
        for i, incident in enumerate(similar_incidents, 1):
            prompt += f"""
### Incident {i} (distance: {incident.get('distance', 'N/A'):.4f})
- **Service:** {incident.get('service', 'unknown')}
- **Symptoms:** {incident.get('symptoms', 'N/A')}
- **Root Cause:** {incident.get('root_cause', 'Not determined')}
- **Fix:** {incident.get('fix', 'Not determined')}
"""
    else:
        prompt += "\nNo similar past incidents found in memory. Reason from first principles.\n"

    prompt += "\nAnalyze this incident and respond with the JSON format specified."
    return prompt


def reason_incident(
    service: str,
    symptoms: str,
    similar_incidents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Use Bedrock LLM to reason over a new incident and propose root cause + fix.

    Args:
        service: The service that triggered the alert.
        symptoms: The alert/symptom text.
        similar_incidents: List of similar past incidents from vector search.

    Returns:
        Dict with keys: root_cause, fix, confidence, reasoning, structured (bool).
        If LLM output can't be parsed, returns raw text with structured=False.
    """
    client = _get_bedrock_client()
    user_prompt = _build_user_prompt(service, symptoms, similar_incidents)

    # Build request body for Claude via Bedrock Messages API
    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
    })

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.invoke_model(
                modelId=LLM_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=request_body,
            )
            response_body = json.loads(response["body"].read())

            # Extract text from Claude's response format
            raw_text = response_body["content"][0]["text"]

            # Try to parse as JSON
            return _parse_llm_response(raw_text)

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF_SECONDS[attempt]
                time.sleep(backoff)
            continue

    # All retries failed
    return {
        "root_cause": f"Unable to determine (LLM error: {last_error})",
        "fix": "Manual investigation required",
        "confidence": "low",
        "reasoning": f"LLM reasoning failed after {MAX_RETRIES} attempts",
        "structured": False,
    }


def _parse_llm_response(raw_text: str) -> Dict[str, Any]:
    """
    Parse the LLM response as JSON. Falls back to returning raw text.
    """
    # Try direct JSON parse
    try:
        # Handle case where LLM wraps JSON in markdown code block
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        result = json.loads(text)
        result["structured"] = True
        return result
    except json.JSONDecodeError:
        pass

    # Fallback: return raw text
    return {
        "root_cause": raw_text[:500],
        "fix": "See raw reasoning output",
        "confidence": "low",
        "reasoning": raw_text,
        "structured": False,
    }
