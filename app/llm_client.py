import openai

from app.config import settings

SYSTEM_PROMPT = (
    "You are a technical analyst. Given the contents of a GitHub repository, "
    "provide a factual summary based solely on the evidence provided. "
    "Do not speculate about features or capabilities not shown in the code."
)

USER_PROMPT_TEMPLATE = """Analyze the following GitHub repository content and provide a structured summary with these sections:

## Overview
A concise description of what this project does and its purpose.

## Technologies
Key languages, frameworks, libraries, and tools used.

## Project Structure
How the codebase is organized (main directories, modules, key files).

## Notable Details
Any interesting patterns, configurations, or architectural decisions.

---

Repository: {repo_name}

{content}
"""


class LLMError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def generate_summary(repo_name: str, content: str) -> str:
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
        return response.choices[0].message.content
    except openai.APITimeoutError:
        raise LLMError("LLM request timed out")
    except openai.APIError as e:
        raise LLMError(f"LLM API error: {e}")
