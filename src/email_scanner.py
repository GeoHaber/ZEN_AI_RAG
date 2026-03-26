#!/usr/bin/env python3
"""
email_scanner.py — Email scanning for RAG_RAT
==============================================

Supports:
  1. IMAP (Gmail, Outlook, Yahoo, custom) — online mailboxes
  2. Local email files (.eml, .mbox)

Returns the same ``(text, images, sources)`` tuple as
``content_extractor.scan_web`` / ``scan_folder``.

Usage::

    from email_scanner import scan_email_imap, scan_email_local

    text, images, sources = scan_email_imap(
        server="imap.gmail.com",
        email_addr="user@gmail.com",
        password="app-password-here",
        folder="INBOX",
        max_emails=100,
        days_back=30,
    )

    text, images, sources = scan_email_local(
        path="C:/Users/me/emails",   # .eml or .mbox files
        max_emails=500,
    )
"""

from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import logging
import mailbox
import re
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  IMAP PRESETS for popular providers
# ═══════════════════════════════════════════════════════════════════════════════

IMAP_PRESETS: Dict[str, Tuple[str, int]] = {
    "gmail": ("imap.gmail.com", 993),
    "outlook": ("outlook.office365.com", 993),
    "hotmail": ("imap-mail.outlook.com", 993),
    "yahoo": ("imap.mail.yahoo.com", 993),
    "aol": ("imap.aol.com", 993),
    "icloud": ("imap.mail.me.com", 993),
    "zoho": ("imap.zoho.com", 993),
}

# Common email folders across providers
COMMON_FOLDERS = [
    "INBOX",
    "Sent",
    "Drafts",
    "Trash",
    "Spam",
    "Archive",
    "[Gmail]/All Mail",
    "[Gmail]/Sent Mail",
    "[Gmail]/Starred",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _decode_header(raw: str | None) -> str:
    """Decode an RFC-2047 encoded email header to plain text."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(data))
    return " ".join(decoded).strip()


def _extract_body(msg: email.message.Message) -> str:
    """Extract the plain-text body from an email Message object."""
    body_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_parts.append(payload.decode(charset, errors="replace"))
            elif ctype == "text/html" and not body_parts:
                # Fallback: strip HTML tags if no plaintext part
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html = payload.decode(charset, errors="replace")
                    body_parts.append(_strip_html(html))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                text = _strip_html(text)
            body_parts.append(text)

    return "\n".join(body_parts).strip()


def _strip_html(html: str) -> str:
    """Rough HTML-to-text (no dependency needed)."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_attachments(msg: email.message.Message) -> List[Dict]:
    """Pull out attachment metadata as image-like dicts."""
    images: List[Dict] = []
    if not msg.is_multipart():
        return images
    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition:
            filename = _decode_header(part.get_filename())
            ctype = part.get_content_type()
            size = len(part.get_payload(decode=True) or b"")
            images.append(
                {
                    "type": "attachment",
                    "filename": filename or "unnamed",
                    "content_type": ctype,
                    "size": size,
                }
            )
    return images


def _parse_date(msg: email.message.Message) -> str:
    """Extract and normalise the Date header → ISO string."""
    raw = msg.get("Date", "")
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        return parsed.isoformat()
    except Exception:
        return raw


def _msg_to_record(
    msg: email.message.Message,
    uid: str = "",
) -> Tuple[str, List[Dict], Dict]:
    """Convert one email.message.Message → (body_text, attachments, source)."""
    subject = _decode_header(msg.get("Subject"))
    sender = _decode_header(msg.get("From"))
    to = _decode_header(msg.get("To"))
    date_str = _parse_date(msg)
    body = _extract_body(msg)
    attachments = _extract_attachments(msg)

    # Compose a structured block of text for RAG indexing
    block = f"Subject: {subject}\nFrom: {sender}\nTo: {to}\nDate: {date_str}\n---\n{body}\n"

    source: Dict = {
        "type": "email",
        "path": f"email://{uid}" if uid else f"email://{subject[:60]}",
        "title": subject or "(no subject)",
        "from": sender,
        "to": to,
        "date": date_str,
        "chars": len(body),
        "attachments": len(attachments),
    }
    return block, attachments, source


# ═══════════════════════════════════════════════════════════════════════════════
#  IMAP SCANNER
# ═══════════════════════════════════════════════════════════════════════════════


def scan_email_imap(
    server: str,
    email_addr: str,
    password: str,
    folder: str = "INBOX",
    max_emails: int = 100,
    days_back: int = 30,
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Scan an IMAP mailbox and return ``(text, images, sources)``.

    Parameters
    ----------
    server : str
        IMAP hostname (e.g. ``imap.gmail.com``).
        Can also be a preset key like ``"gmail"``, ``"outlook"``.
    email_addr : str
        Full email address (login username).
    password : str
        Password or app-specific password.
    folder : str
        Mailbox folder to scan (default ``"INBOX"``).
    max_emails : int
        Max messages to fetch (newest first).
    days_back : int
        Only fetch messages from the last N days.
    progress_callback : optional
        ``callback(done, total)`` — called after each email.

    Returns
    -------
    (str, List[Dict], List[Dict])
        Combined text, attachments list, source list.
    """
    # Resolve preset aliases → real hostname
    preset = IMAP_PRESETS.get(server.lower().strip())
    if preset:
        server, port = preset
    else:
        port = 993

    all_text: list[str] = []
    all_images: list[Dict] = []
    all_sources: list[Dict] = []

    ctx = ssl.create_default_context()
    try:
        conn = imaplib.IMAP4_SSL(server, port, ssl_context=ctx)
    except Exception as exc:
        logger.error("IMAP connection to %s:%d failed: %s", server, port, exc)
        raise ConnectionError(f"Cannot connect to {server}:{port} — {exc}") from exc

    try:
        conn.login(email_addr, password)
    except imaplib.IMAP4.error as exc:
        conn.logout()
        raise PermissionError(f"Login failed for {email_addr} — check password / app-password") from exc

    try:
        status, _ = conn.select(f'"{folder}"', readonly=True)
        if status != "OK":
            conn.logout()
            raise FileNotFoundError(f'Mailbox folder "{folder}" not found')

        # Build date search criterion
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        _, msg_nums = conn.search(None, f'(SINCE "{since_date}")')
        uid_list = msg_nums[0].split() if msg_nums[0] else []
        # Newest first, cap at max_emails
        uid_list = uid_list[-max_emails:][::-1]
        total = len(uid_list)
        logger.info("IMAP %s/%s — %d messages to fetch", server, folder, total)

        for idx, uid in enumerate(uid_list):
            try:
                _, data = conn.fetch(uid, "(RFC822)")
                raw = data[0][1] if data and data[0] else None
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)
                body, attachments, source = _msg_to_record(msg, uid=uid.decode("ascii", errors="replace"))
                all_text.append(body)
                all_images.extend(attachments)
                all_sources.append(source)
            except Exception as exc:
                logger.warning("Failed to parse UID %s: %s", uid, exc)

            if progress_callback:
                try:
                    progress_callback(idx + 1, total)
                except Exception as exc:
                    logger.debug("%s", exc)
    finally:
        try:
            conn.close()
        except Exception as exc:
            logger.debug("%s", exc)
        conn.logout()

    combined = "\n\n".join(all_text)
    logger.info(
        "IMAP scan done: %d emails, %d chars, %d attachments",
        len(all_sources),
        len(combined),
        len(all_images),
    )
    return combined, all_images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCAL EMAIL FILE SCANNER  (.eml / .mbox)
# ═══════════════════════════════════════════════════════════════════════════════


def scan_email_local(
    path: str,
    max_emails: int = 500,
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Scan local ``.eml`` files or ``.mbox`` archives.

    Parameters
    ----------
    path : str
        Path to a folder of ``.eml`` files, a single ``.mbox`` file,
        or a single ``.eml`` file.
    max_emails : int
        Maximum messages to process.
    progress_callback : optional
        ``callback(done, total)``

    Returns
    -------
    (str, List[Dict], List[Dict])
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    all_text: list[str] = []
    all_images: list[Dict] = []
    all_sources: list[Dict] = []

    messages: list[Tuple[str, email.message.Message]] = []

    if p.is_file() and p.suffix.lower() == ".mbox":
        mbox = mailbox.mbox(str(p))
        for key, msg in mbox.items():
            messages.append((f"mbox:{key}", msg))
            if len(messages) >= max_emails:
                break
        mbox.close()
    elif p.is_file() and p.suffix.lower() == ".eml":
        with open(p, "rb") as f:
            msg = email.message_from_bytes(f.read())
        messages.append((p.name, msg))
    elif p.is_dir():
        eml_files = sorted(p.rglob("*.eml"))[:max_emails]
        mbox_files = sorted(p.rglob("*.mbox"))
        for ef in eml_files:
            try:
                with open(ef, "rb") as f:
                    msg = email.message_from_bytes(f.read())
                messages.append((str(ef), msg))
            except Exception as exc:
                logger.warning("Cannot parse %s: %s", ef, exc)
            if len(messages) >= max_emails:
                break
        for mf in mbox_files:
            if len(messages) >= max_emails:
                break
            try:
                mbox = mailbox.mbox(str(mf))
                for key, msg in mbox.items():
                    messages.append((f"{mf.name}:{key}", msg))
                    if len(messages) >= max_emails:
                        break
                mbox.close()
            except Exception as exc:
                logger.warning("Cannot parse mbox %s: %s", mf, exc)
    else:
        raise FileNotFoundError(f"Path is not a directory, .eml, or .mbox file: {path}")

    total = len(messages)
    logger.info("Local email scan — %d messages to process", total)

    for idx, (uid, msg) in enumerate(messages):
        try:
            body, attachments, source = _msg_to_record(msg, uid=uid)
            all_text.append(body)
            all_images.extend(attachments)
            all_sources.append(source)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", uid, exc)

        if progress_callback:
            try:
                progress_callback(idx + 1, total)
            except Exception as exc:
                logger.debug("%s", exc)

    combined = "\n\n".join(all_text)
    logger.info("Local email scan done: %d emails, %d chars", len(all_sources), len(combined))
    return combined, all_images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  UNIFIED ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def scan_email(
    mode: str = "imap",
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Unified entry point.

    Parameters
    ----------
    mode : str
        ``"imap"`` for online IMAP scanning, ``"local"`` for .eml/.mbox files.
    **kwargs
        Forwarded to ``scan_email_imap()`` or ``scan_email_local()``.
    """
    if mode == "local":
        return scan_email_local(**kwargs)
    return scan_email_imap(**kwargs)
