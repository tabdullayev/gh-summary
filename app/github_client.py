import httpx

from app.config import settings


class GitHubError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


async def get_repo_info(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=_headers(),
        )
    _check_response(resp)
    return resp.json()


async def get_tree(owner: str, repo: str, branch: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
            headers=_headers(),
        )
    _check_response(resp)
    data = resp.json()
    return data.get("tree", [])


async def get_file_content(owner: str, repo: str, branch: str, path: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}",
            headers=_headers(),
        )
    _check_response(resp)
    return resp.text


def _check_response(resp: httpx.Response) -> None:
    if resp.status_code == 404:
        raise GitHubError("Repository or resource not found", status_code=404)
    if resp.status_code == 403:
        raise GitHubError("GitHub API rate limit exceeded", status_code=429)
    if resp.status_code >= 400:
        raise GitHubError(
            f"GitHub API error: {resp.status_code}", status_code=502
        )
