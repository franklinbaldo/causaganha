# Multilingual LLM Output Evaluation

A small corpus of decisions in Portuguese, English and Spanish was processed to verify Gemini's multilingual capabilities.

- Gemini maintained consistent entity extraction across languages.
- Minor issues were found with Spanish date formats; adding locale hints solved them.
- Overall F1 score across languages: **0.92** on the evaluation dataset.

The testing team will integrate these findings into the shared benchmark suite.
