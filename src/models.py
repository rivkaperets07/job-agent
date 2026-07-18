from dataclasses import dataclass, field


@dataclass
class JobPosting:
    title: str
    company: str
    url: str
    source: str
    location: str = ""
    snippet: str = ""
    received_at: str = ""

    @property
    def dedupe_key(self) -> str:
        return self.url or f"{self.source}:{self.title}:{self.company}"


@dataclass
class Classification:
    job: JobPosting
    relevant: bool
    relevance_reason: str
    is_likely_fake: bool
    fake_reasons: list[str] = field(default_factory=list)
    apply_probability: int = 0
    apply_reasons: str = ""
