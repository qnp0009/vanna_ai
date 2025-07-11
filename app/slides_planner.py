import requests
import re
import os
import json
from dotenv import load_dotenv

load_dotenv()

def clean_slide_json_response(text):
    try:
        # Remove <think>...</think> blocks if present
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # Extract from first [ to last ]
        start_index = text.find("[")
        end_index = text.rfind("]") + 1

        if start_index == -1 or end_index == -1:
            raise ValueError("No JSON array found in text.")

        json_text = text[start_index:end_index]

        # Clean up
        json_text = json_text.strip("` \n")

        # Parse JSON
        parsed = json.loads(json_text)

        # Filter valid slides
        slides = [
            s for s in parsed
            if isinstance(s, dict)
            and s.get("title")
            and s.get("content")
        ]

        return slides

    except Exception as e:
        print("❌ Failed to clean slide JSON:", e)
        return []

def deduplicate_charts(slides: list[dict]) -> list[dict]:
    seen_charts = set()
    deduped_slides = []

    for slide in slides:
        # Convert chart key to string to make it hashable
        chart_key = str((
            slide.get("chart_column"),
            slide.get("chart_value"),
            slide.get("chart_type")
        ))

        if all([slide.get("chart_column"), slide.get("chart_value"), slide.get("chart_type")]) and chart_key in seen_charts:
            # Chart already exists → remove chart from this slide
            slide["chart_column"] = None
            slide["chart_value"] = None
            slide["chart_type"] = None
        elif all([slide.get("chart_column"), slide.get("chart_value"), slide.get("chart_type")]):
            # First time seeing this chart → mark as used
            seen_charts.add(chart_key)

        deduped_slides.append(slide)

    return deduped_slides


def ask_llm_for_slides(report_text, metadata, api_key=None, base_url=None):
    if api_key is None:
        api_key = os.getenv("LLM_API_KEY")
    if base_url is None:
        base_url = os.getenv("LLM_API_URL", "https://vibe-agent-gateway.eternalai.org")
    
    prompt = f"""
You are a skilled data presentation assistant.

Given:
- A structured **dataset overview** (columns and types):  
{metadata}

- A detailed **data analysis report** written in natural language:  
{report_text}

🎯 Your job:
Convert the report into a sequence of high-quality presentation slides (like in PowerPoint or Reveal.js).
It should have a slide for introduction and one for conclusion.
If using chart in slides, make sure do not use any chart twice.

Each slide must have:
- "title": short, informative
- "content": a list of bullet points (each max ~20 words)
- Optional: chart suggestions to enrich specific slides

Return a valid JSON list:

[
  {{
    "title": "Slide title",
    "content": ["• Point 1", "• Point 2", ...],
    "chart_column": "group_by_column or null",
    "chart_value": "value_column for sum/avg (if chart used) or null",
    "chart_type": "bar, pie, histogram, line or null"
  }},
  ...
]

📊 Chart Guidelines:
- "bar" → sum of `chart_value` grouped by `chart_column` (e.g., total tax by city)
- "pie" → proportion of `chart_value` by `chart_column`
- "histogram" → distribution of a numeric column
- "line" → trend over time (x = time-like column)
- If no clear chart benefit → set all chart fields to null

🎨 Slide Formatting:
- Keep content max 5–6 bullet points per slide
- If the report is long, split it into multiple coherent slides
- Always include a **Conclusion** slide at the end with summary or takeaways
- Use actual column names from the dataset for charts

Return JSON only. Do not include explanations or markdown.
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"]
        slides = clean_slide_json_response(raw_text)
        return slides
    except Exception as e:
        print("❌ Error calling LLM:", e)
        return []
