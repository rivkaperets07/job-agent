import json
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from src.models import Classification, JobPosting

MODEL = "gemini-2.5-flash"
BATCH_SIZE = 8
MAX_RETRIES = 5

_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "relevant": {"type": "boolean"},
                    "relevance_reason": {"type": "string"},
                    "is_likely_fake": {"type": "boolean"},
                    "fake_reasons": {"type": "array", "items": {"type": "string"}},
                    "apply_probability": {"type": "integer"},
                    "apply_reasons": {"type": "string"},
                },
                "required": [
                    "index",
                    "relevant",
                    "relevance_reason",
                    "is_likely_fake",
                    "fake_reasons",
                    "apply_probability",
                    "apply_reasons",
                ],
            },
        }
    },
    "required": ["results"],
}

_SYSTEM_TEMPLATE = """Sos un asistente que triagea avisos de trabajo para un usuario.

Preferencias e instrucciones del usuario (usalas para decidir relevancia):
---
{preferences}
---

Para cada aviso de la lista, evaluá tres cosas:

1. `relevant`: ¿el aviso matchea las preferencias del usuario? `relevance_reason` en 1 frase.
2. `is_likely_fake`: ¿hay señales de que sea un aviso falso o scam? (piden plata, urgencia \
artificial, salario absurdo para el rol, sin info real de la empresa, lenguaje tipo MLM, \
pide datos financieros antes de una entrevista). `fake_reasons` es una lista de las señales \
concretas encontradas (vacía si no hay ninguna).
3. `apply_probability`: 0-100, qué tan probable es que el usuario pueda aplicar y tenga chances \
reales (cumple requisitos excluyentes, no pide algo que claramente no tiene según sus \
preferencias). `apply_reasons` en 1-2 frases.

Devolvé un resultado por cada aviso, en el mismo orden que la lista de entrada, usando el \
campo `index` para identificar cada uno (0-indexado)."""


def classify_jobs(
    client: genai.Client, preferences: str, jobs: list[JobPosting]
) -> list[Classification]:
    results: list[Classification] = []
    for start in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[start : start + BATCH_SIZE]
        results.extend(_classify_batch(client, preferences, batch))
    return results


def _classify_batch(
    client: genai.Client, preferences: str, batch: list[JobPosting]
) -> list[Classification]:
    payload = [
        {
            "index": i,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "snippet": job.snippet,
        }
        for i, job in enumerate(batch)
    ]

    text = _generate_with_retry(
        client,
        system=_SYSTEM_TEMPLATE.format(preferences=preferences),
        content=json.dumps(payload, ensure_ascii=False),
    )
    parsed = json.loads(text)

    classifications: list[Classification] = []
    for item in parsed["results"]:
        job = batch[item["index"]]
        classifications.append(
            Classification(
                job=job,
                relevant=item["relevant"],
                relevance_reason=item["relevance_reason"],
                is_likely_fake=item["is_likely_fake"],
                fake_reasons=item["fake_reasons"],
                apply_probability=item["apply_probability"],
                apply_reasons=item["apply_reasons"],
            )
        )
    return classifications


def _generate_with_retry(client: genai.Client, system: str, content: str) -> str:
    """El free tier de Gemini tiene rate limits bajos (requests por minuto) — con
    varios cientos de lotes en la primera corrida, es normal pisar el límite.
    Reintenta con backoff en vez de abortar todo el proceso."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=_SCHEMA,
                ),
            )
            return response.text
        except ClientError as e:
            is_rate_limit = getattr(e, "code", None) == 429
            if not is_rate_limit or attempt == MAX_RETRIES - 1:
                raise
            wait = 10 * (attempt + 1)
            print(f"Rate limit de Gemini, esperando {wait}s (intento {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
    raise RuntimeError("unreachable")
