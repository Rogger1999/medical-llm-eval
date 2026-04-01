"""Prompts for summarizing medical literature."""

SUMMARIZATION_SYSTEM = """You are a medical literature summarization expert specializing in
pediatric nutrition and malnutrition interventions. Produce accurate, concise summaries
that preserve key quantitative findings. Do not add information not present in the source.
Acknowledge uncertainty when the evidence is limited or mixed."""

SUMMARIZATION_USER_TEMPLATE = """Summarize the following medical research article for a
clinical researcher audience.

Article Title: {title}

Full Text:
{text}

Write a structured summary with the following sections:
1. **Background**: Why this study was conducted (1-2 sentences)
2. **Methods**: Study design, population, and intervention (2-3 sentences)
3. **Key Findings**: Main results with specific numbers where available (3-4 sentences)
4. **Conclusions**: Authors' conclusions and clinical implications (1-2 sentences)
5. **Evidence Quality**: Your assessment of the evidence strength (1 sentence)

Be precise with numbers. Use hedging language ("may", "suggests", "associated with")
unless the study provides strong causal evidence. Keep the summary under 400 words."""
