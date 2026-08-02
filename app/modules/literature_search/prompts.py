"""Prompt construction for candidate extraction only."""

from app.modules.literature_search.query_model import MAX_RETMX

PROMPT_VERSION = "search-intent-v1"


def build_candidate_prompt(raw_topic: str) -> str:
    return f"""Extract conservative candidate fields from the user's medical literature topic.
Return JSON only with topic, disease, intervention, target, mechanism, date_range,
study_types, language, exclusions, retmax. date_range is {{start_year,end_year,original_expression}}.
Do not invent entities or expand abbreviations. Leave unknown values null or []. Do not write a final
search expression and do not force PICO. retmax must be 1-{MAX_RETMX}. The user will review every field.
Topic: {raw_topic}"""
