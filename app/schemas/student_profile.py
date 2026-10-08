from datetime import date

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


class AcademicProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_year: int = Field(ge=1900, le=2100)
    group_name: str = Field(min_length=1, max_length=120)
    campus_name: str = Field(min_length=1, max_length=120)
    linkedin_url: AnyHttpUrl | None = None
    github_url: AnyHttpUrl | None = None

    @field_validator("group_name", "campus_name")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Academic profile text cannot be empty")
        return normalized

    @field_validator("linkedin_url", "github_url")
    @classmethod
    def validate_profile_domain(cls, value: AnyHttpUrl | None, info):
        if value is None:
            return None
        host = value.host.lower().rstrip(".")
        provider = "linkedin.com" if info.field_name == "linkedin_url" else "github.com"
        if host != provider and not host.endswith(f".{provider}"):
            raise ValueError(f"The {info.field_name} URL must belong to {provider}")
        return value

    @model_validator(mode="after")
    def validate_profile(self):
        if self.start_year > date.today().year:
            raise ValueError("Start year cannot be in the future")
        return self


class AcademicProfileResponse(BaseModel):
    start_year: int
    group_name: str
    campus_name: str
    linkedin_url: str | None = None
    github_url: str | None = None
