"""
Reasoning module - uses OpenAI or Bedrock LLM to analyze an incident,
propose a root cause + fix, and optionally generate a code patch.

Usage:
    from agent.reason import reason_incident
    result = reason_incident(service, symptoms, similar_incidents, code_context)
"""

import json
import time
import boto3
from typing import List, Dict, Any, Optional
from openai import OpenAI

from agent.skills import load_skill_context

from agent.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_LLM_MODEL,
    AWS_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    LLM_MODEL_ID,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
)


SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) and software developer investigating a production incident.

Given a current alert, similar past incidents from memory, and optionally the source code where the bug exists, analyze the situation and propose:
1. The most likely root cause
2. A specific fix/remediation step
3. Your confidence level (high, medium, low)
4. Brief reasoning
5. If source code is provided AND confidence is "high", provide a code_patch with the exact fix

You MUST respond with valid JSON in exactly this format:
{
  "root_cause": "concise description of the root cause",
  "fix": "specific actionable remediation step",
  "confidence": "high|medium|low",
  "reasoning": "brief explanation",
  "code_patch": {
    "file": "filename.py",
    "find": "exact code to replace (copy from source)",
    "replace": "fixed code"
  }
}

If you cannot provide a code_patch (low confidence or no source code), set code_patch to null.
Only provide code_patch when you are CERTAIN about the fix."""


def reason_incident(
    service: str,
    symptoms: str,
    similar_incidents: List[Dict[str, Any]],
    code_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reason over an incident and propose root cause + fix.

    Args:
        service: The service that triggered the alert.
        symptoms: The alert/symptom text.
        similar_incidents: List of similar past incidents from vector search.
        code_context: Optional source code of the affected file for self-healing.

    Returns:
        Dict with: root_cause, fix, confidence, reasoning, code_patch (or None).
    """
    user_prompt = _build_user_prompt(service, symptoms, similar_incidents, code_context)

    if LLM_PROVIDER == "openai":
        return _reason_openai(user_prompt)
    else:
        return _reason_bedrock(user_prompt)


def _build_user_prompt(
    service: str,
    symptoms: str,
    similar_incidents: List[Dict[str, Any]],
    code_context: Optional[str] = None,
) -> str:
    """Build the user prompt with alert, similar incidents, and optional code."""
    prompt = f"""## Current Alert
- **Service:** {service}
- **Symptoms:** {symptoms}

## Similar Past Incidents from Memory
"""
    if similar_incidents:
        for i, incident in enumerate(similar_incidents[:3], 1):
            prompt += f"""
### Incident {i} (distance: {incident.get('distance', 'N/A'):.4f})
- **Service:** {incident.get('service', 'unknown')}
- **Symptoms:** {incident.get('symptoms', 'N/A')}
- **Root Cause:** {incident.get('root_cause', 'Not determined')}
- **Fix:** {incident.get('fix', 'Not determined')}
"""
    else:
        prompt += "\nNo similar past incidents found in memory.\n"

    if code_context:
        prompt += f"""
## Source Code (affected file)
```
{code_context}
```

Analyze the code above for the bug causing the reported symptoms. If you can identify the exact fix, provide it in code_patch.
"""

    # Load relevant CockroachDB skill for context
    skill = load_skill_context(symptoms)
    if skill:
        print(f"  [skills] ✓ Loaded skill: {skill['name']} ({len(skill['content'])} chars)")
        prompt += f"""
## CockroachDB Best Practices (from skill: {skill['name']})
{skill['content']}
"""
    else:
        print(f"  [skills] No matching skill found for these symptoms")

    prompt += "\nRespond with the JSON format specified in the system prompt."
    return prompt


def _reason_openai(user_prompt: str) -> Dict[str, Any]:
    """Reason using OpenAI GPT."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=OPENAI_LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw_text = response.choices[0].message.content
            return _parse_llm_response(raw_text)

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS[attempt])
            continue

    return {
        "root_cause": f"Unable to determine (LLM error: {last_error})",
        "fix": "Manual investigation required",
        "confidence": "low",
        "reasoning": f"LLM reasoning failed after {MAX_RETRIES} attempts",
        "code_patch": None,
        "structured": False,
    }


def _reason_bedrock(user_prompt: str) -> Dict[str, Any]:
    """Reason using Bedrock Claude."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    client = boto3.client("bedrock-runtime", **kwargs)

    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
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
            raw_text = response_body["content"][0]["text"]
            return _parse_llm_response(raw_text)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS[attempt])
            continue

    return {
        "root_cause": f"Unable to determine (LLM error: {last_error})",
        "fix": "Manual investigation required",
        "confidence": "low",
        "reasoning": f"LLM reasoning failed after {MAX_RETRIES} attempts",
        "code_patch": None,
        "structured": False,
    }


def _parse_llm_response(raw_text: str) -> Dict[str, Any]:
    """Parse the LLM response as JSON."""
    try:
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
        if "code_patch" not in result:
            result["code_patch"] = None
        return result
    except json.JSONDecodeError:
        pass

    return {
        "root_cause": raw_text[:500],
        "fix": "See raw reasoning output",
        "confidence": "low",
        "reasoning": raw_text,
        "code_patch": None,
        "structured": False,
    }
