from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from services.ses_service import SESService


router = APIRouter(
    prefix="/test",
    tags=["test"],
)


class SendTestEmailRequest(BaseModel):
    to_email: EmailStr
    auditor_name_or_email: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None

    # When omitted, we send a simple "today + 2h" event.
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    meeting_url: Optional[str] = None


def _build_google_calendar_event_url(
    *,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    details: str = "",
    location: str = "",
) -> str:
    def _fmt(dt: datetime) -> str:
        # "Floating" timestamp: interpreted in recipient's local timezone by Google Calendar UI.
        return dt.strftime("%Y%m%dT%H%M%S")

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{_fmt(start_dt)}/{_fmt(end_dt)}",
    }
    if details:
        params["details"] = details
    if location:
        params["location"] = location
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


@router.post("/email")
async def send_test_email(
    body: SendTestEmailRequest,
):
    """
    Test-only endpoint to send a sample email via SES.
    """
    now = datetime.now()
    start_dt = body.start_at or (now + timedelta(hours=2))
    end_dt = body.end_at or (start_dt + timedelta(hours=1))

    city = (body.city or "Boston").strip()
    zip_code = (body.zip or "02108").strip()
    location = " ".join([p for p in [city, zip_code] if p])

    details_lines: list[str] = []
    if (body.meeting_url or "").strip():
        details_lines.append(f"Meeting link: {body.meeting_url.strip()}")
    details_lines.append("Sent from test endpoint.")

    title_city_zip = " ".join([p for p in [city, zip_code] if p])
    title = f"Audit - {title_city_zip}".strip() if title_city_zip else "Audit"
    google_calendar_url = _build_google_calendar_event_url(
        title=title,
        start_dt=start_dt,
        end_dt=end_dt,
        details="\n".join(details_lines),
        location=location,
    )

    src_root = Path(__file__).resolve().parents[1]
    template_path = src_root / "services" / "email_templates" / "auditor_notification.html"

    ses = SESService()
    ses.send_email_from_html_template(
        to_addresses=[str(body.to_email)],
        subject="Souzet (TEST): New audit location assigned",
        template_path=template_path,
        context={
            "auditor_name_or_email": (body.auditor_name_or_email or str(body.to_email)).strip(),
            "city": city,
            "zip": zip_code,
            "date": start_dt.strftime("%B %d, %Y"),
            "time": start_dt.strftime("%I:%M %p").lstrip("0"),
            "google_calendar_url": google_calendar_url,
        },
    )

    return {"status": "sent", "to": str(body.to_email)}

