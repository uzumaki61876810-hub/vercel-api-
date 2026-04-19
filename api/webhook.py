"""
Stripe webhook handler
POST /api/webhook

Flow:
  1. Stripe sends checkout.session.completed event
  2. We verify the signature
  3. Extract customer info from metadata
  4. Generate PDF report
  5. Send email via SendGrid
"""
import os
import sys
import json
import tempfile
import base64
import traceback
from http.server import BaseHTTPRequestHandler

# Add lib to path for generate_report / astro_calc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition, ContentId
)

# ── env vars ──
STRIPE_SECRET_KEY     = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
SENDGRID_API_KEY      = os.environ.get('SENDGRID_API_KEY', '')
FROM_EMAIL            = os.environ.get('FROM_EMAIL', 'info@goddess-diagnosis.com')
FROM_NAME             = os.environ.get('FROM_NAME', '星と命の金運鑑定局')

stripe.api_key = STRIPE_SECRET_KEY


def send_report_email(to_email: str, to_name: str, pdf_bytes: bytes) -> dict:
    """Send PDF report via SendGrid."""
    encoded = base64.b64encode(pdf_bytes).decode()

    message = Mail(
        from_email=(FROM_EMAIL, FROM_NAME),
        to_emails=[(to_email, to_name)],
        subject='【星と命の金運鑑定局】完全鑑定レポートをお届けします',
        html_content=f'''
<div style="font-family: 'Hiragino Mincho ProN', Georgia, serif; max-width:600px; margin:0 auto; background:#0D1B2A; color:#FAF8F4; padding:40px 30px; border-radius:8px;">
  <div style="text-align:center; border-bottom:1px solid #C9A84C; padding-bottom:20px; margin-bottom:30px;">
    <p style="color:#C9A84C; letter-spacing:.2em; font-size:12px;">✦ 星と命の金運鑑定局 ✦</p>
    <h1 style="font-size:22px; font-weight:normal; margin:10px 0;">完全鑑定レポートのお届け</h1>
  </div>
  <p>{to_name} 様</p>
  <p style="line-height:1.9; color:#D4C9E8;">
    この度はお申し込みいただき、誠にありがとうございます。<br>
    四柱推命と西洋占星術のダブルアプローチで読み解いた、<br>
    あなただけの完全鑑定レポートをお届けします。
  </p>
  <div style="background:#1A2E45; border:1px solid #C9A84C; border-radius:6px; padding:20px; margin:24px 0; text-align:center;">
    <p style="color:#C9A84C; font-size:13px; margin:0;">📎 添付ファイルをご確認ください</p>
    <p style="font-size:12px; color:#B8BEC7; margin-top:8px;">完全鑑定レポート.pdf</p>
  </div>
  <p style="line-height:1.9; color:#D4C9E8;">
    レポートはPDF形式でお送りしています。<br>
    ご不明な点がございましたら、お気軽にご連絡ください。
  </p>
  <div style="border-top:1px solid #1A2E45; padding-top:20px; margin-top:30px; text-align:center;">
    <p style="color:#B8BEC7; font-size:11px;">星と命の金運鑑定局<br>{FROM_EMAIL}</p>
  </div>
</div>
'''
    )

    attachment = Attachment()
    attachment.file_content = FileContent(encoded)
    attachment.file_type = FileType('application/pdf')
    attachment.file_name = FileName('完全鑑定レポート.pdf')
    attachment.disposition = Disposition('attachment')
    attachment.content_id = ContentId('report_pdf')
    message.attachment = attachment

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    return {'status': response.status_code}


def send_error_notification(to_email: str, to_name: str, error: str) -> None:
    """Notify customer if PDF generation fails (fallback)."""
    message = Mail(
        from_email=(FROM_EMAIL, FROM_NAME),
        to_emails=[(to_email, to_name)],
        subject='【星と命の金運鑑定局】レポート準備中のお知らせ',
        html_content=f'''
<div style="font-family: Georgia, serif; max-width:600px; margin:0 auto; padding:40px 30px;">
  <p>{to_name} 様</p>
  <p>お申し込みを確認いたしました。レポートの作成に少々お時間をいただいております。
     24時間以内に改めてお送りいたします。</p>
  <p>星と命の金運鑑定局</p>
</div>
'''
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)


def process_checkout_session(session: dict) -> dict:
    """
    Core processing: extract data → generate PDF → send email.
    Returns status dict.
    """
    # ── Extract customer info ──
    customer_email = session.get('customer_details', {}).get('email', '')
    customer_name  = session.get('customer_details', {}).get('name', '')
    metadata       = session.get('metadata', {})

    # Fields passed as Stripe metadata from apply-lp.html
    user_data = {
        'name':              customer_name or metadata.get('name', ''),
        'birthdate':         metadata.get('birthdate', ''),
        'birth_time':        metadata.get('birth_time', ''),
        'birth_place':       metadata.get('birth_place', ''),
        'concern':           metadata.get('concern', 'income'),
        # 四柱推命 pillars (calculated client-side or here)
        'year_pillar':       metadata.get('year_pillar', ''),
        'month_pillar':      metadata.get('month_pillar', ''),
        'day_pillar':        metadata.get('day_pillar', ''),
        'day_main_star':     metadata.get('day_main_star', ''),
        'month_center_star': metadata.get('month_center_star', ''),
        'day_juunun':        metadata.get('day_juunun', ''),
        'month_juunun':      metadata.get('month_juunun', ''),
        # 西洋占星術
        'sun_sign':          metadata.get('sun_sign', ''),
        'moon_sign':         metadata.get('moon_sign', ''),
        'asc':               metadata.get('asc', ''),
        'mc':                metadata.get('mc', ''),
        # 複合タイプ
        'composite_type':    metadata.get('composite_type', ''),
        'energy_pct':        int(metadata.get('energy_pct', 75)),
    }

    # ── Generate PDF ──
    from generate_report import generate_report

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name

    generate_report(user_data, tmp_path)

    with open(tmp_path, 'rb') as f:
        pdf_bytes = f.read()

    os.unlink(tmp_path)

    # ── Send email ──
    result = send_report_email(customer_email, customer_name, pdf_bytes)
    return {
        'email': customer_email,
        'pdf_size': len(pdf_bytes),
        'sendgrid_status': result['status']
    }


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function (Python runtime)."""

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_length)
        sig_header = self.headers.get('Stripe-Signature', '')

        # ── Verify Stripe signature ──
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as e:
            self._respond(400, {'error': 'Invalid signature'})
            return
        except Exception as e:
            self._respond(400, {'error': str(e)})
            return

        # ── Handle event ──
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            try:
                result = process_checkout_session(session)
                self._respond(200, {'ok': True, **result})
            except Exception as e:
                # Try to send fallback email
                try:
                    email = session.get('customer_details', {}).get('email', '')
                    name  = session.get('customer_details', {}).get('name', '')
                    if email:
                        send_error_notification(email, name, str(e))
                except Exception:
                    pass
                self._respond(500, {'error': str(e), 'trace': traceback.format_exc()})
        else:
            # Other events — acknowledge
            self._respond(200, {'ok': True, 'event': event['type']})

    def do_GET(self):
        self._respond(200, {'status': 'Stripe webhook endpoint active'})

    def _respond(self, status: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # suppress default logging
