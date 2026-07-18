import base64
from email.mime.text import MIMEText


def send_digest(service, to_email: str, subject: str, html_body: str) -> None:
    message = MIMEText(html_body, "html")
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
