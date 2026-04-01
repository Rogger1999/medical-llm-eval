"""Prompts for grounding verification (LLM-as-judge)."""

GROUNDING_CHECK_SYSTEM = """You are an expert medical fact-checker evaluating whether
an AI-generated answer is grounded in the provided source evidence.

For each key claim in the answer, determine whether it is:
- SUPPORTED: directly supported by the provided context
- INFERRED: a reasonable inference from the context but not explicitly stated
- UNSUPPORTED: not present in the context or contradicts it

Return a JSON object with your assessment."""

GROUNDING_CHECK_USER_TEMPLATE = """Evaluate whether the following answer is grounded
in the provided source context.

Answer to evaluate:
{answer}

Source context:
{context}

For each key claim in the answer, check if it is supported by the context.
Return a JSON object in this exact format:
{{
  "grounding_score": 0.0,
  "total_claims": 0,
  "supported_claims": 0,
  "inferred_claims": 0,
  "unsupported_claims": 0,
  "unsupported_details": ["list of unsupported claims"],
  "assessment": "brief overall assessment"
}}

grounding_score should be between 0.0 (completely ungrounded) and 1.0 (fully grounded).
Inferred claims count as 0.5 toward grounding."""
