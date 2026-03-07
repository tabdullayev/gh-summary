from app.config import settings
from app import github_client

EXCLUDED_DIRS = {
    ".git", "node_modules", "vendor", "__pycache__", "dist", "build",
    "target", ".next", ".nuxt", ".venv", "venv", "env",
}

EXCLUDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".wasm", ".pyc",
    ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin", ".dat", ".db",
    ".sqlite", ".lock", ".map", ".min.js", ".min.css", ".ttf", ".woff",
    ".woff2", ".eot", ".mp3", ".mp4", ".zip", ".tar", ".gz", ".pdf",
}

LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Pipfile.lock",
    "poetry.lock", "Gemfile.lock", "composer.lock", "Cargo.lock",
}

CONFIG_FILES = {
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "go.sum",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", "CMakeLists.txt", "setup.py", "setup.cfg",
    "tsconfig.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile", "composer.json", ".github/workflows",
}

ENTRY_PATTERNS = {
    "main.py", "app.py", "index.ts", "index.js", "main.ts", "main.js",
    "main.go", "main.rs", "lib.rs", "index.html", "manage.py",
    "src/main.py", "src/main.ts", "src/main.js", "src/index.ts",
    "src/index.js", "src/main.rs", "src/lib.rs", "src/main.go",
    "src/app.py", "cmd/main.go",
}


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def _is_excluded(path: str) -> bool:
    parts = path.split("/")
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    if parts[-1] in LOCK_FILES:
        return True
    for ext in EXCLUDED_EXTENSIONS:
        if path.endswith(ext):
            return True
    return False


def _truncate(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > 0:
        truncated = truncated[:last_newline]
    return truncated + "\n... [truncated]"


def _build_directory_tree(tree_entries: list[dict], max_depth: int = 4) -> str:
    lines = []
    for entry in sorted(tree_entries, key=lambda e: e["path"]):
        path = entry["path"]
        if _is_excluded(path):
            continue
        depth = path.count("/")
        if depth >= max_depth:
            continue
        indent = "  " * depth
        name = path.split("/")[-1]
        if entry["type"] == "tree":
            lines.append(f"{indent}{name}/")
        else:
            lines.append(f"{indent}{name}")
    return "\n".join(lines)


def _is_config_file(path: str) -> bool:
    filename = path.split("/")[-1]
    if filename in CONFIG_FILES:
        return True
    if path in CONFIG_FILES:
        return True
    # Check for workflow files
    if path.startswith(".github/workflows") and path.endswith((".yml", ".yaml")):
        return True
    return False


def _is_entry_point(path: str) -> bool:
    filename = path.split("/")[-1]
    return filename in {p.split("/")[-1] for p in ENTRY_PATTERNS} or path in ENTRY_PATTERNS


def _is_source_file(path: str) -> bool:
    source_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
        ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
        ".kt", ".scala", ".clj", ".ex", ".exs", ".hs", ".ml",
        ".vue", ".svelte",
    }
    return any(path.endswith(ext) for ext in source_extensions)


def _is_test_file(path: str) -> bool:
    lower = path.lower()
    return (
        "test" in lower
        or "spec" in lower
        or lower.startswith("tests/")
        or "/tests/" in lower
        or "/test/" in lower
        or "/__tests__/" in lower
    )


async def select_content(
    owner: str, repo: str, branch: str, tree_entries: list[dict]
) -> tuple[str, int]:
    """Select and assemble repo content within token budget. Returns (content, tokens_used)."""
    budget = settings.TOKEN_BUDGET
    tokens_used = 0
    sections: list[str] = []

    blob_entries = [e for e in tree_entries if e["type"] == "blob" and not _is_excluded(e["path"])]

    # P0: README
    readme_path = None
    for entry in blob_entries:
        if entry["path"].lower() in ("readme.md", "readme.rst", "readme.txt", "readme"):
            if "/" not in entry["path"]:  # root only
                readme_path = entry["path"]
                break

    if readme_path:
        p0_budget = min(3000, budget)
        content = await github_client.get_file_content(owner, repo, branch, readme_path)
        content = _truncate(content, p0_budget)
        tokens = estimate_tokens(content)
        sections.append(f"=== {readme_path} ===\n{content}")
        tokens_used += tokens
        budget -= tokens

    # P1: Directory tree
    p1_budget = min(1500, budget)
    dir_tree = _build_directory_tree(tree_entries)
    dir_tree = _truncate(dir_tree, p1_budget)
    tree_tokens = estimate_tokens(dir_tree)
    sections.append(f"=== Directory Structure ===\n{dir_tree}")
    tokens_used += tree_tokens
    budget -= tree_tokens

    # P2: Config files
    p2_budget = min(3000, budget)
    p2_used = 0
    config_entries = [e for e in blob_entries if _is_config_file(e["path"])]
    for entry in config_entries:
        if p2_used >= p2_budget:
            break
        cap = min(800, p2_budget - p2_used)
        content = await github_client.get_file_content(owner, repo, branch, entry["path"])
        content = _truncate(content, cap)
        tokens = estimate_tokens(content)
        sections.append(f"=== {entry['path']} ===\n{content}")
        p2_used += tokens
    tokens_used += p2_used
    budget -= p2_used

    # P3: Entry points
    p3_budget = min(2500, budget)
    p3_used = 0
    entry_entries = [e for e in blob_entries if _is_entry_point(e["path"]) and not _is_config_file(e["path"])]
    for entry in entry_entries:
        if p3_used >= p3_budget:
            break
        cap = min(800, p3_budget - p3_used)
        content = await github_client.get_file_content(owner, repo, branch, entry["path"])
        content = _truncate(content, cap)
        tokens = estimate_tokens(content)
        sections.append(f"=== {entry['path']} ===\n{content}")
        p3_used += tokens
    tokens_used += p3_used
    budget -= p3_used

    # P4: Other source files (sorted by path depth, skip tests)
    other_sources = [
        e for e in blob_entries
        if _is_source_file(e["path"])
        and not _is_test_file(e["path"])
        and not _is_config_file(e["path"])
        and not _is_entry_point(e["path"])
    ]
    other_sources.sort(key=lambda e: e["path"].count("/"))

    for entry in other_sources:
        if budget <= 0:
            break
        cap = min(500, budget)
        content = await github_client.get_file_content(owner, repo, branch, entry["path"])
        content = _truncate(content, cap)
        tokens = estimate_tokens(content)
        sections.append(f"=== {entry['path']} ===\n{content}")
        tokens_used += tokens
        budget -= tokens

    return "\n\n".join(sections), tokens_used
