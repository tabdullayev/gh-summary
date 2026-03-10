import json

import openai

from app.config import settings

SYSTEM_PROMPT = (
    "You are a technical analyst. Given the contents of a GitHub repository, "
    "provide a factual summary based solely on the evidence provided. "
    "Do not speculate about features or capabilities not shown in the code."
)

USER_PROMPT_TEMPLATE = """Analyze the following GitHub repository content and respond with a JSON object containing exactly these three fields:

- "summary": A human-readable description of what the project does.
- "technologies": A list of strings of the main technologies, languages, and frameworks used.
- "structure": A brief description of the project structure.

Respond ONLY with valid JSON, no markdown fences, no extra text.

---

Repository: {repo_name}

{content}
"""


class LLMError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def generate_summary(repo_name: str, content: str) -> dict:
    client = openai.AsyncOpenAI(
        api_key=settings.NEBIUS_API_KEY,
        base_url=settings.NEBIUS_BASE_URL,
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(repo_name=repo_name, content=content)

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout=60.0,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise LLMError("LLM returned invalid JSON")
    except openai.APITimeoutError:
        raise LLMError("LLM request timed out")
    except openai.APIError as e:
        raise LLMError(f"LLM API error: {e}")
