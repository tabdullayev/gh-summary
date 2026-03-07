import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.models import SummarizeRequest, SummarizeResponse
from app.github_client import GitHubError, get_repo_info, get_tree
from app.content_selector import select_content
from app.llm_client import LLMError, generate_summary

app = FastAPI(title="GitHub Repository Summarizer")


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from a GitHub URL."""
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/?#]+)", str(url)
    )
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")
    return owner, repo


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "gh-summary"}


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    owner, repo = parse_github_url(str(request.github_url))
    repo_full = f"{owner}/{repo}"

    # Get repo info and tree
    info = await get_repo_info(owner, repo)
    branch = info.get("default_branch", "main")
    tree_entries = await get_tree(owner, repo, branch)

    # Select content within token budget
    content, tokens_used = await select_content(owner, repo, branch, tree_entries)

    # Generate summary via LLM
    summary = await generate_summary(repo_full, content)

    total_files = sum(1 for e in tree_entries if e["type"] == "blob")
    return SummarizeResponse(
        repository=repo_full,
        summary=summary,
        metadata={
            "default_branch": branch,
            "total_files": total_files,
            "tokens_used": tokens_used,
        },
    )


@app.exception_handler(GitHubError)
async def github_error_handler(request, exc: GitHubError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request, exc: LLMError):
    return JSONResponse(
        status_code=502,
        content={"detail": exc.message},
    )
