"""Prompt construction kept separate so model text is auditable and replaceable."""

PROMPT_VERSION = "r3-wp02-v1"


def build_topic_structuring_prompt(topic: str) -> str:
    """Request conservative JSON without inventing medical facts."""
    return f"""Extract only concepts explicitly supported by this public research topic: {topic!r}.
Return JSON with structuring_status (pico, peco, mechanism, or unstructured), reason,
disease, intervention, target, mechanism, comparator, outcome, study_type, focus_points,
and clarification_questions. Each clarification question has question and clarifies_field.
Use the shared names disease/intervention/target/mechanism. Never invent facts. If the topic
does not support a PICO-like template, use unstructured with a reason and focus_points."""
