import json
import anthropic

SYSTEM_PROMPT = """You are a business analyst specializing in health-tech and wellness startups.
Given a company name, URL, and a snippet of web content, extract structured information.
Respond ONLY with valid JSON — no markdown, no explanation."""

USER_TEMPLATE = """Analyze this company and return a JSON object with exactly these fields:
{{
  "name": "company name (infer from title/url if needed)",
  "description": "1-2 sentence description of what they do",
  "business_model": one of ["subscription", "freemium", "one-time", "marketplace", "B2B", "unknown"],
  "ai_usage": true or false,
  "ai_details": "brief description of how they use AI, or null if they don't"
}}

Title: {title}
URL: {url}
Content snippet: {content}"""


def analyze_company(title: str, url: str, content: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    prompt = USER_TEMPLATE.format(
        title=title,
        url=url,
        content=content[:1500],  # keep tokens reasonable
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
