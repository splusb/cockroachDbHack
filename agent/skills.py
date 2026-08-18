"""
Skills module — loads relevant CockroachDB SKILL.md files for the LLM.

Maps incident symptoms to relevant skills, reads the file, and extracts
a concise context snippet that gets included in the reasoning prompt.
"""

import os
from typing import Optional, Dict

# Base path to skills directory
SKILLS_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "skills"
)

# Maps keywords in symptoms to skill paths (relative to SKILLS_BASE)
SKILL_KEYWORD_MAP = {
    # Schema & SQL issues
    "column": "cockroachdb-query-and-schema-design/cockroachdb-sql",
    "schema": "cockroachdb-query-and-schema-design/cockroachdb-sql",
    "table": "cockroachdb-query-and-schema-design/cockroachdb-sql",
    "insert": "cockroachdb-application-development/designing-application-transactions",
    "select": "cockroachdb-query-and-schema-design/cockroachdb-sql",
    "query": "cockroachdb-query-and-schema-design/cockroachdb-sql",
    # Transaction issues
    "transaction": "cockroachdb-application-development/designing-application-transactions",
    "retry": "cockroachdb-application-development/designing-application-transactions",
    "40001": "cockroachdb-application-development/designing-application-transactions",
    "serialization": "cockroachdb-application-development/designing-application-transactions",
    "deadlock": "cockroachdb-application-development/designing-application-transactions",
    # Performance
    "timeout": "cockroachdb-observability-and-diagnostics/profiling-statement-fingerprints",
    "slow": "cockroachdb-observability-and-diagnostics/profiling-statement-fingerprints",
    "latency": "cockroachdb-observability-and-diagnostics/profiling-statement-fingerprints",
    "performance": "cockroachdb-observability-and-diagnostics/profiling-statement-fingerprints",
    # Connection & operations
    "connection": "cockroachdb-operations-and-lifecycle/reviewing-cluster-health",
    "pool": "cockroachdb-application-development/designing-application-transactions",
    # Security
    "password": "cockroachdb-security-and-governance/enforcing-password-policies",
    "authentication": "cockroachdb-security-and-governance/hardening-user-privileges",
    "permission": "cockroachdb-security-and-governance/hardening-user-privileges",
    # Multi-region
    "region": "cockroachdb-application-development/designing-multi-region-applications",
}

# Max chars to extract from a skill file (keep LLM context reasonable)
MAX_SKILL_CHARS = 3000


def match_skill(symptoms: str) -> Optional[str]:
    """
    Given symptoms, return the skill path that's most relevant.
    Returns the relative path under SKILLS_BASE, or None.
    """
    symptoms_lower = symptoms.lower()
    for keyword, skill_path in SKILL_KEYWORD_MAP.items():
        if keyword in symptoms_lower:
            return skill_path
    return None


def load_skill_context(symptoms: str) -> Optional[Dict[str, str]]:
    """
    Load the relevant SKILL.md file content for the given symptoms.
    
    Returns:
        Dict with 'name', 'path', and 'content' (truncated), or None.
    """
    skill_path = match_skill(symptoms)
    if not skill_path:
        return None

    skill_file = os.path.join(SKILLS_BASE, skill_path, "SKILL.md")
    if not os.path.exists(skill_file):
        return None

    try:
        with open(skill_file, "r") as f:
            content = f.read()

        # Extract the frontmatter description and first few sections
        summary = _extract_summary(content)

        return {
            "name": skill_path.split("/")[-1],
            "category": skill_path.split("/")[0],
            "path": skill_path,
            "content": summary,
        }
    except Exception as e:
        print(f"[skills] Error loading {skill_file}: {e}")
        return None


def _extract_summary(content: str) -> str:
    """
    Extract a useful summary from a SKILL.md file.
    Takes the description from frontmatter + first few sections up to MAX_SKILL_CHARS.
    """
    lines = content.split("\n")
    output = []
    in_frontmatter = False
    chars = 0

    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            # Include description from frontmatter
            if line.startswith("description:"):
                output.append(line.replace("description:", "SKILL:").strip())
                chars += len(line)
            continue

        # Skip empty lines at start
        if not output and not line.strip():
            continue

        output.append(line)
        chars += len(line)

        if chars >= MAX_SKILL_CHARS:
            output.append("\n[... truncated for context ...]")
            break

    return "\n".join(output)
