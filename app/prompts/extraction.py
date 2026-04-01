"""Prompts for structured data extraction from medical literature."""

EXTRACTION_SYSTEM = """You are a medical research data extraction specialist.
Extract structured information from clinical research articles about malnutrition
and nutritional interventions in children. Be precise and factual.
Extract only information explicitly stated in the text — do not infer or extrapolate.
Return your response as a valid JSON object."""

EXTRACTION_USER_TEMPLATE = """Extract structured information from the following medical article.

Article Title: {title}

Article Text:
{text}

Extract the following fields and return them as a JSON object:
{{
  "title": "Article title",
  "population": "Study population description (age, location, n=?, inclusion criteria)",
  "intervention": "Description of the nutritional intervention(s) tested",
  "comparator": "Control group or comparison condition",
  "outcomes": ["list of primary and secondary outcomes measured"],
  "numeric_values": {{
    "sample_size": null,
    "duration_weeks": null,
    "effect_size": null,
    "p_value": null,
    "confidence_interval": null
  }},
  "adverse_events": "Any reported adverse events or safety concerns",
  "conclusion": "Authors' main conclusion in 1-2 sentences",
  "evidence_snippets": ["2-3 direct quotes supporting key claims"],
  "evidence_level": "RCT/observational/meta-analysis/review/other",
  "limitations": "Key study limitations mentioned"
}}

Use null for any field not found in the text. Do not fabricate information."""
