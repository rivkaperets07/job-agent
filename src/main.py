import argparse
import datetime
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src import gmail_client, storage
from src.classifier import build_client, classify_jobs
from src.digest import build_digest_html
from src.mailer import send_digest
from src.parsers.linkedin import parse_linkedin_alert

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREFERENCES_PATH = PROJECT_ROOT / "preferences.md"
LAST_RUN_KEY = "last_run_date"


def main(dry_run: bool = False, limit: int | None = None) -> None:
    conn = storage.connect()
    preferences = PREFERENCES_PATH.read_text(encoding="utf-8")

    creds = gmail_client.get_credentials()
    service = gmail_client.build_service(creds)

    after_date = storage.get_state(conn, LAST_RUN_KEY)
    message_ids = gmail_client.fetch_alert_message_ids(service, after_date)
    print(f"Mails de alerta encontrados: {len(message_ids)}")

    jobs = []
    seen_keys: set[str] = set()
    for msg_id in message_ids:
        html = gmail_client.get_message_html(service, msg_id)
        for job in parse_linkedin_alert(html):
            if job.dedupe_key in seen_keys:
                continue
            seen_keys.add(job.dedupe_key)
            jobs.append(job)

    new_jobs = [j for j in jobs if not storage.is_seen(conn, j)]
    print(f"Avisos nuevos (sin duplicados): {len(new_jobs)}")

    if limit is not None:
        new_jobs = new_jobs[:limit]
        print(f"--limit activo: probando solo con {len(new_jobs)} avisos")

    classifications = []
    if new_jobs:
        client = build_client()
        classifications = classify_jobs(client, preferences, new_jobs)
        for c in classifications:
            storage.save_classification(conn, c)

    today = datetime.date.today()
    digest_html = build_digest_html(classifications, today.isoformat())

    if dry_run:
        print(digest_html)
    else:
        to_email = os.environ["DIGEST_TO_EMAIL"]
        send_digest(
            service, to_email, f"Resumen de trabajo — {today.isoformat()}", digest_html
        )
        print(f"Resumen enviado a {to_email}")

    if limit is None:
        storage.set_state(conn, LAST_RUN_KEY, today.strftime("%Y/%m/%d"))
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime el resumen en vez de enviarlo por mail (para probar el pipeline)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Clasifica como máximo N avisos nuevos (para probar sin agotar cuotas de "
        "API). No avanza el puntero de última corrida, así el resto del backlog "
        "sigue disponible para una corrida completa después.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run, limit=args.limit)
