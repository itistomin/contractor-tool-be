import os
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any, Iterable

import boto3
from botocore.exceptions import ClientError


@dataclass(frozen=True)
class SESEmailResult:
    message_id: str


class SESService:
    """
    Service for sending emails with AWS Simple Email Service (SES).

    Supports:
    - Sending HTML (and optional text) bodies
    - Rendering HTML template files with variable substitution
    """

    def __init__(self):
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        # Support both AWS_REGION and AWS_BUCKET_REGION for backward compatibility
        self.aws_region = os.getenv("AWS_BUCKET_REGION") or os.getenv("AWS_REGION", "us-east-1")
        self.from_email = os.getenv("SES_FROM_EMAIL")
        self.configuration_set = os.getenv("SES_CONFIGURATION_SET")  # optional

        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.from_email]):
            raise ValueError(
                "Missing required SES configuration. Please set AWS_ACCESS_KEY_ID, "
                "AWS_SECRET_ACCESS_KEY, and SES_FROM_EMAIL environment variables."
            )

        self.ses_client = boto3.client(
            "ses",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
        )

    def render_html_template(self, template_path: str | Path, context: dict[str, Any]) -> str:
        """
        Render an HTML template file.

        Supports both:
        - `$variable` placeholders (string.Template)
        - `{{variable}}` placeholders

        Example template snippet:
            <p>Hello $first_name</p>
        """
        path = Path(template_path)
        html = path.read_text(encoding="utf-8")
        safe_context = {k: ("" if v is None else str(v)) for k, v in (context or {}).items()}
        rendered = Template(html).safe_substitute(safe_context)

        def replace_curly(match: re.Match[str]) -> str:
            key = (match.group(1) or "").strip()
            return safe_context.get(key, "")

        return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace_curly, rendered)

    def send_email_html(
        self,
        *,
        to_addresses: Iterable[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
        reply_to_addresses: Iterable[str] | None = None,
    ) -> SESEmailResult:
        to_list = [a.strip() for a in to_addresses if a and str(a).strip()]
        if not to_list:
            raise ValueError("to_addresses must contain at least one email address")

        message: dict[str, Any] = {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
        }
        if text_body is not None:
            message["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}

        request: dict[str, Any] = {
            "Source": self.from_email,
            "Destination": {"ToAddresses": to_list},
            "Message": message,
        }
        if reply_to_addresses:
            request["ReplyToAddresses"] = [a.strip() for a in reply_to_addresses if a and str(a).strip()]
        if self.configuration_set:
            request["ConfigurationSetName"] = self.configuration_set

        try:
            resp = self.ses_client.send_email(**request)
            return SESEmailResult(message_id=resp["MessageId"])
        except ClientError as e:
            raise Exception(f"Failed to send SES email: {str(e)}")

    def send_email_from_html_template(
        self,
        *,
        to_addresses: Iterable[str],
        subject: str,
        template_path: str | Path,
        context: dict[str, Any] | None = None,
        text_body: str | None = None,
        reply_to_addresses: Iterable[str] | None = None,
    ) -> SESEmailResult:
        html_body = self.render_html_template(template_path, context or {})
        return self.send_email_html(
            to_addresses=to_addresses,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            reply_to_addresses=reply_to_addresses,
        )


def test_send_email() -> str:
    """
    Simple test helper to verify SES config works.

    Requires env:
    - SES_TEST_TO_EMAIL
    - (optional) SES_TEST_SUBJECT
    """
    to_email = (os.getenv("SES_TEST_TO_EMAIL") or "").strip()
    if not to_email:
        raise ValueError("Missing SES_TEST_TO_EMAIL environment variable")

    subject = (os.getenv("SES_TEST_SUBJECT") or "SES test email").strip()
    html_body = "<html><body><p>This is a test email sent via AWS SES.</p></body></html>"

    ses = SESService()
    result = ses.send_email_html(to_addresses=[to_email], subject=subject, html_body=html_body)
    return result.message_id


if __name__ == "__main__":
    message_id = test_send_email()
    print(f"SES message sent. MessageId={message_id}")
