import base64
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

TOKEN_PATH = Path(__file__).resolve().parent.parent / "token.json"
CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "credentials.json"

# Remitentes de alertas de trabajo a rastrear. Sumá más a medida que te lleguen
# de otras fuentes (Indeed, Computrabajo, etc.).
ALERT_SENDERS = [
    "jobalerts-noreply@linkedin.com",
    "jobs-noreply@linkedin.com",
]


def get_credentials() -> Credentials:
    """Carga credenciales desde variables de entorno (CI) o hace el flujo
    interactivo de OAuth (primera corrida en local)."""
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
        return creds

    if not CREDENTIALS_PATH.exists():
        raise RuntimeError(
            "No hay credenciales de Gmail. Descargá credentials.json desde Google Cloud "
            "Console (OAuth client ID, tipo 'Desktop app') y colocalo en la raíz del "
            "proyecto. Ver README.md para el paso a paso."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def build_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds)


def build_query(after_date: str | None) -> str:
    sender_filter = " OR ".join(f"from:{s}" for s in ALERT_SENDERS)
    query = f"({sender_filter})"
    if after_date:
        query += f" after:{after_date}"
    return query


def fetch_alert_message_ids(service, after_date: str | None) -> list[str]:
    query = build_query(after_date)
    ids: list[str] = []
    page_token = None
    while True:
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token)
            .execute()
        )
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_message_html(service, msg_id: str) -> str:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    return _extract_html(msg["payload"])


def _extract_html(payload: dict) -> str:
    if payload.get("mimeType") == "text/html" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", errors="replace"
        )
    for part in payload.get("parts", []) or []:
        html = _extract_html(part)
        if html:
            return html
    return ""
