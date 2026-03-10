# GitHub Repository Summarizer

A FastAPI service that accepts a GitHub repo URL and returns an LLM-generated summary of the project.

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
```

Required:
- `NEBIUS_API_KEY` — Your Nebius API key

Optional:
- `GITHUB_TOKEN` — GitHub personal access token (for higher rate limits)

## Run

```bash
uvicorn app.main:app --reload
```

## Usage

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/psf/requests"}'
```

## API

- `GET /` — Health check
- `POST /summarize` — Summarize a GitHub repository
  - Body: `{"github_url": "https://github.com/owner/repo"}`
  - Returns: `summary` (text), `technologies` (list), `structure` (text)

## Model Choice

This service uses **Qwen/Qwen3-Coder-30B-A3B-Instruct** hosted on Nebius. It's a code-specialized model that strikes a good balance between quality and speed — 30B total parameters with only 3B active at inference time thanks to Mixture-of-Experts (MoE) architecture.

## Content Handling

Not everything in a repository is useful for summarization. The service uses a **priority-based token budget** (12,000 tokens total) to select the most informative files:

| Priority | Content | Token Cap |
|----------|---------|-----------|
| P0 | README | 3,000 |
| P1 | Directory tree (4 levels deep) | 1,500 |
| P2 | Config files (package.json, pyproject.toml, etc.) | 3,000 |
| P3 | Entry points (main.py, index.js, etc.) | 2,500 |
| P4 | Other source files | Remaining budget |

**Excluded from processing:**
- Directories: `.git`, `node_modules`, `vendor`, `__pycache__`, `dist`, `build`, `.venv`, etc.
- Files: binaries, images, lock files (`package-lock.json`, `yarn.lock`, etc.), minified files, test files
- Extensions: `.png`, `.jpg`, `.wasm`, `.pyc`, `.so`, `.exe`, `.lock`, `.min.js`, `.min.css`, etc.

The directory tree is capped at **4 levels deep** to keep structural context useful without overwhelming the token budget on deeply nested projects.

## Disclaimer

This app was 100% built by Claude.
