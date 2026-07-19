import os

from src.models import Classification, JobPosting

PROVIDER = os.environ.get("CLASSIFIER_PROVIDER", "claude")

if PROVIDER == "gemini":
    from src.classifier_gemini import classify_jobs as _classify_jobs
elif PROVIDER == "claude":
    from src.classifier_claude import classify_jobs as _classify_jobs
else:
    raise RuntimeError(
        f"CLASSIFIER_PROVIDER inválido: {PROVIDER!r} (usá 'claude' o 'gemini')"
    )


def classify_jobs(client, preferences: str, jobs: list[JobPosting]) -> list[Classification]:
    return _classify_jobs(client, preferences, jobs)


def build_client():
    if PROVIDER == "gemini":
        from google import genai

        return genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    from anthropic import Anthropic

    return Anthropic()
