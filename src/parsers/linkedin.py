from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.models import JobPosting


def parse_linkedin_alert(html: str, received_at: str = "") -> list[JobPosting]:
    """Extrae avisos de trabajo de un mail de alerta de LinkedIn.

    Heurístico: LinkedIn no tiene una plantilla de mail estable y documentada
    públicamente, así que esto busca links a /jobs/view/ y el texto/hermanos
    cercanos para título, empresa y ubicación. Si LinkedIn cambia su plantilla,
    puede hacer falta ajustar `_find_company_and_location` mirando el HTML de
    un mail real (Gmail > ver mensaje original).
    """
    soup = BeautifulSoup(html, "html.parser")
    postings: list[JobPosting] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/jobs/view/" not in href and "/comm/jobs/view/" not in href:
            continue

        clean_url = _clean_job_url(href)
        if clean_url in seen_urls:
            continue

        title = link.get_text(strip=True)
        if not title:
            continue

        company, location = _find_company_and_location(link)
        seen_urls.add(clean_url)
        postings.append(
            JobPosting(
                title=title,
                company=company,
                location=location,
                url=clean_url,
                source="linkedin",
                snippet=title,
                received_at=received_at,
            )
        )
    return postings


def _clean_job_url(href: str) -> str:
    parsed = urlparse(href)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _find_company_and_location(link_tag) -> tuple[str, str]:
    container = link_tag.find_parent("table") or link_tag.parent
    if not container:
        return "", ""
    text_blocks = [t.strip() for t in container.stripped_strings if t.strip()]
    company = text_blocks[1] if len(text_blocks) > 1 else ""
    location = text_blocks[2] if len(text_blocks) > 2 else ""
    return company, location
