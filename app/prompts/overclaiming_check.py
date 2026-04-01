"""Prompts for overclaiming detection (LLM-as-judge)."""

OVERCLAIMING_CHECK_SYSTEM = """You are an expert in medical research methodology and
evidence-based medicine. Your role is to identify overclaiming in AI-generated medical
summaries and answers.

Overclaiming includes:
1. Presenting correlational evidence as causation ("X causes Y" when study shows association)
2. Generalizing animal or in-vitro evidence to human outcomes
3. Presenting preliminary or weak evidence as definitive conclusions
4. Claiming treatment efficacy beyond what the study design supports
5. Ignoring study limitations when making strong recommendations

Return a JSON object listing any overclaiming instances found."""

OVERCLAIMING_CHECK_USER_TEMPLATE = """Review the following medical text for instances
of overclaiming or inappropriate certainty.

Article title: {title}

Text to evaluate:
{answer}

Identify any instances where the text:
- Implies causation from correlational data
- Overgeneralizes findings beyond the study population
- Presents weak evidence as conclusive
- Makes clinical recommendations unsupported by the evidence level

Return a JSON object:
{{
  "overclaiming_instances": [
    {{
      "quote": "exact problematic phrase",
      "issue_type": "causation|generalization|certainty|recommendation",
      "explanation": "why this is overclaiming",
      "suggested_correction": "more appropriate phrasing"
    }}
  ],
  "overall_assessment": "appropriate|minor_issues|significant_overclaiming"
}}"""
