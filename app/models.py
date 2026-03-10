from pydantic import BaseModel, HttpUrl, field_validator


class SummarizeRequest(BaseModel):
    github_url: HttpUrl

    @field_validator("github_url")
    @classmethod
    def must_be_github(cls, v: HttpUrl) -> HttpUrl:
        if "github.com" not in str(v):
            raise ValueError("URL must be a github.com repository URL")
        return v


class SummarizeResponse(BaseModel):
    summary: str
    technologies: list[str]
    structure: str
