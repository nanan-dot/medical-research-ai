"""Versioned prompt for a concise, evidence-grounded beginner reading report."""

TEMPLATE_VERSION = "general-v1"
MAX_PROMPT_CHARACTERS = 16_000
FIELD_NAMES = (
    "basic_information",
    "one_sentence_conclusion",
    "research_background",
    "research_question",
    "study_type",
    "population",
    "sample_size",
    "intervention_or_exposure",
    "comparator",
    "primary_outcome",
    "statistical_methods",
    "main_results",
    "innovations",
    "limitations",
    "next_questions",
    "original_evidence",
    "pending_items",
)


def build_analysis_prompt() -> str:
    fields = ", ".join(FIELD_NAMES)
    prompt = f"""Analyze only the indexed paper. Return one JSON object with exactly these fields: {fields}.
Each field must be an object: {{"value": string, "kind": "fact|summary|inference|not_found", "source_indices": [zero-based integers]}}.
Use not_found and value 未找到 when the paper provides no evidence. Never invent missing methods, numbers, conclusions, DOI, or medical claims. Distinguish direct facts, summaries, and inference. Preserve sample sizes and result numbers exactly as supported. source_indices refer only to the sources returned with this answer. Keep the report concise and understandable to a first-year graduate student. Return JSON only."""
    if len(prompt) > MAX_PROMPT_CHARACTERS:
        raise ValueError("Analysis prompt is too long")
    return prompt
