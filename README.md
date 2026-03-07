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
  - Returns: repository name, LLM summary, and metadata
