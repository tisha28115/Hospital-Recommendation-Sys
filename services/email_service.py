from __future__ import annotations

import html
import json
import smtplib
from email.message import EmailMessage
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from config import settings


class EmailDeliveryError(Exception):
    pass


def _escape(value: Any) -> str:
    return html.escape(str(value if value is not None else "-"))


def email_config_status() -> tuple[bool, str]:
    if settings.resend_api_key:
        if not settings.smtp_sender_email:
            return False, "Email notifications are not configured. Missing: SMTP_SENDER_EMAIL"
        return True, "Email notifications are configured with Resend."

    missing = [
        key
        for key, value in {
            "SMTP_HOST": settings.smtp_host,
            "SMTP_USERNAME": settings.smtp_username,
            "SMTP_PASSWORD": settings.smtp_password,
            "SMTP_SENDER_EMAIL": settings.smtp_sender_email,
        }.items()
        if not value
    ]
    if missing:
        return False, f"Email notifications are not configured. Missing: {', '.join(missing)}"
    return True, "Email notifications are configured."


def build_hospital_maps_link(appointment: dict[str, Any]) -> str:
    latitude = appointment.get("hospital_latitude")
    longitude = appointment.get("hospital_longitude")
    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps?q={latitude},{longitude}"

    hospital_name = str(appointment.get("hospital_name", "")).strip()
    hospital_city = str(appointment.get("hospital_city", "")).strip()
    query = " ".join(part for part in [hospital_name, hospital_city] if part)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}" if query else "https://www.google.com/maps"


def _build_appointment_email_content(
    *,
    recipient_name: str,
    appointment: dict[str, Any],
) -> tuple[str, str, str]:
    maps_link = build_hospital_maps_link(appointment)
    hospital_name = str(appointment.get("hospital_name", "your selected hospital")).strip()
    hospital_city = str(appointment.get("hospital_city", "")).strip()
    city_line = f" ({hospital_city})" if hospital_city else ""
    subject = f"Appointment Confirmed - {hospital_name}"

    text_body = "\n".join(
        [
            f"Hello {recipient_name or 'User'},",
            "",
            "Your appointment has been confirmed.",
            f"Hospital: {hospital_name}{city_line}",
            f"Disease: {appointment.get('disease', '-')}",
            f"Department: {appointment.get('department', '-')}",
            f"Severity: {appointment.get('severity', '-')}",
            f"Appointment Date: {appointment.get('appointment_date', '-')}",
            f"Appointment Time: {appointment.get('appointment_time', '-')}",
            "",
            f"Hospital location on Google Maps: {maps_link}",
            "",
            "Please arrive a little early and keep this email for reference.",
            "",
            "Regards,",
            settings.smtp_sender_name,
        ]
    )

    html_body = f"""
    <html>
      <body style="margin:0; padding:24px; background:#f6efe7; font-family:Georgia, 'Times New Roman', serif; color:#2f2a26;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
          <tr>
            <td align="center">
              <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px; background:#fffaf4; border-radius:24px; overflow:hidden; box-shadow:0 16px 40px rgba(120, 79, 42, 0.12);">
                <tr>
                  <td style="background:#c56a43; color:#fffaf4; padding:24px 32px; text-align:center;">
                    <h1 style="margin:0; font-size:28px; line-height:1.2;">Appointment Confirmed</h1>
                    <p style="margin:10px 0 0; font-size:15px; opacity:0.92;">Your hospital booking has been successfully scheduled.</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:32px;">
                    <p style="margin:0 0 20px; font-size:17px;">Hello {_escape(recipient_name or 'User')},</p>
                    <p style="margin:0 0 24px; font-size:16px; line-height:1.7;">
                      Your appointment is confirmed. Please review the details below and keep this email handy for your visit.
                    </p>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse; background:#fff; border:1px solid #eadbcf; border-radius:18px; overflow:hidden;">
                      <tr>
                        <td style="padding:14px 18px; width:38%; font-weight:700; color:#7b4a33; border-bottom:1px solid #eadbcf;">Hospital</td>
                        <td style="padding:14px 18px; border-bottom:1px solid #eadbcf;">{_escape(hospital_name)}{_escape(city_line)}</td>
                      </tr>
                      <tr>
                        <td style="padding:14px 18px; font-weight:700; color:#7b4a33; border-bottom:1px solid #eadbcf;">Disease</td>
                        <td style="padding:14px 18px; border-bottom:1px solid #eadbcf;">{_escape(appointment.get('disease', '-'))}</td>
                      </tr>
                      <tr>
                        <td style="padding:14px 18px; font-weight:700; color:#7b4a33; border-bottom:1px solid #eadbcf;">Department</td>
                        <td style="padding:14px 18px; border-bottom:1px solid #eadbcf;">{_escape(appointment.get('department', '-'))}</td>
                      </tr>
                      <tr>
                        <td style="padding:14px 18px; font-weight:700; color:#7b4a33; border-bottom:1px solid #eadbcf;">Severity</td>
                        <td style="padding:14px 18px; border-bottom:1px solid #eadbcf;">{_escape(appointment.get('severity', '-'))}</td>
                      </tr>
                      <tr>
                        <td style="padding:14px 18px; font-weight:700; color:#7b4a33; border-bottom:1px solid #eadbcf;">Appointment Date</td>
                        <td style="padding:14px 18px; border-bottom:1px solid #eadbcf;">{_escape(appointment.get('appointment_date', '-'))}</td>
                      </tr>
                      <tr>
                        <td style="padding:14px 18px; font-weight:700; color:#7b4a33;">Appointment Time</td>
                        <td style="padding:14px 18px;">{_escape(appointment.get('appointment_time', '-'))}</td>
                      </tr>
                    </table>
                    <div style="margin:28px 0 18px; text-align:center;">
                      <a href="{html.escape(maps_link, quote=True)}" style="display:inline-block; padding:14px 22px; background:#2f6f5e; color:#fffaf4; text-decoration:none; border-radius:999px; font-size:15px; font-weight:700;">
                        Open Hospital in Google Maps
                      </a>
                    </div>
                    <p style="margin:0 0 10px; font-size:15px; line-height:1.7;">
                      Please arrive a little early and carry any required medical documents with you.
                    </p>
                    <p style="margin:18px 0 0; font-size:15px; line-height:1.7;">
                      Regards,<br />{_escape(settings.smtp_sender_name)}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    return subject, text_body, html_body


def _send_with_resend(
    *,
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    payload = {
        "from": f"{settings.smtp_sender_name} <{settings.smtp_sender_email}>",
        "to": [recipient_email],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }
    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "hospital-recommendation-app/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            if response.status >= 400:
                response_body = response.read().decode("utf-8", errors="replace")
                raise EmailDeliveryError(f"Resend rejected the email: {response_body}")
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise EmailDeliveryError(f"Resend rejected the email: {response_body}") from exc
    except EmailDeliveryError:
        raise
    except Exception as exc:
        raise EmailDeliveryError(f"Unable to send appointment confirmation email with Resend: {exc}") from exc


def _send_with_smtp(
    *,
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    email_message = EmailMessage()
    email_message["Subject"] = subject
    email_message["From"] = f"{settings.smtp_sender_name} <{settings.smtp_sender_email}>"
    email_message["To"] = recipient_email
    email_message.set_content(text_body)
    email_message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(email_message)
    except Exception as exc:
        raise EmailDeliveryError(f"Unable to send appointment confirmation email: {exc}") from exc


def send_appointment_confirmation_email(
    *,
    recipient_email: str,
    recipient_name: str,
    appointment: dict[str, Any],
) -> None:
    ready, message = email_config_status()
    if not ready:
        raise EmailDeliveryError(message)

    subject, text_body, html_body = _build_appointment_email_content(
        recipient_name=recipient_name,
        appointment=appointment,
    )
    if settings.resend_api_key:
        _send_with_resend(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return

    _send_with_smtp(
        recipient_email=recipient_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
