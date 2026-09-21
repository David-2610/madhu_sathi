"""
QR code generation service for Honey Chain.

Generates QR codes encoding public trace URLs.
Supports both SVG vector output and PNG binary/data-URL output.
"""

import base64
import io
from typing import Optional

import qrcode
import qrcode.image.svg


def generate_qr_svg(content: str) -> str:
    """Generate an SVG vector string encoding *content*."""
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
        image_factory=factory,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image()
    stream = io.BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")


def generate_qr_png_bytes(content: str, box_size: int = 10, border: int = 4) -> bytes:
    """Generate raw PNG bytes encoding *content*."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_data_url(content: str) -> str:
    """Generate a base64-encoded data URL suitable for <img> src embedding."""
    png_bytes = generate_qr_png_bytes(content)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_trace_url(base_url: str, trace_token: str) -> str:
    """Construct a full canonical trace URL using *base_url* and *trace_token*."""
    clean_base = base_url.rstrip("/")
    return f"{clean_base}/trace/{trace_token}"
