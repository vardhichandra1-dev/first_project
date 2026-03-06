"""
Email Cache Manager
--------------------
Fetches up to 3 days of emails from Gmail, stores them locally as JSON,
and serves them without hitting the API again until explicitly refreshed.

Cache file: data/email_cache.json (relative to the project root)

Stored per email:
  id, subject, sender, sender_email, date_raw, date_iso, timestamp_unix,
  snippet, body (plain text), has_attachments, attachments (list of dicts),
  thread_id, labels, category, account_id, cached_at
"""

import os
import json
import base64
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

# Path to cache file – relative to project root (two levels up from this file)
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_BACKEND    = os.path.dirname(_THIS_DIR)
_PROJECT    = os.path.dirname(_BACKEND)
CACHE_DIR   = os.path.join(_PROJECT, "data")
CACHE_FILE  = os.path.join(CACHE_DIR, "email_cache.json")

CACHE_DAYS  = 3   # how many days of email history to keep / re-fetch


# ── Date helpers ────────────────────────────────────────────────────

def _parse_date_to_iso(date_str: str) -> tuple[str, float]:
    """
    Parse an RFC 2822 email date string.
    Returns (iso_string, unix_timestamp). Falls back gracefully.
    """
    if not date_str or date_str == "Unknown":
        now = datetime.now(timezone.utc)
        return now.isoformat(), now.timestamp()

    # Strip timezone label in parens e.g. "(IST)"
    date_str = re.sub(r"\s+\([^)]+\)$", "", date_str).strip()

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(), dt.timestamp()
        except ValueError:
            pass

    # Last resort: strip ±HHMM offset and retry
    try:
        clean = re.sub(r"[+-]\d{4}$", "", date_str).strip()
        dt = datetime.strptime(clean, "%a, %d %b %Y %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat(), dt.timestamp()
    except Exception:
        now = datetime.now(timezone.utc)
        return now.isoformat(), now.timestamp()


# ── Body / attachment extraction ────────────────────────────────────

def _decode_b64(data: str) -> str:
    """Decode a Gmail URL-safe base64 string to UTF-8 text."""
    try:
        padded = data + "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_body_and_attachments(payload: dict) -> tuple[str, list]:
    """
    Recursively walk the MIME payload tree.
    Returns (plain_text_body, attachments_list).

    Each attachment dict:
      {name, mime_type, size_bytes, attachment_id}
    """
    body_text   = ""
    attachments = []

    mime = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if not parts:
        # Leaf node
        body_data = payload.get("body", {}).get("data", "")
        att_id    = payload.get("body", {}).get("attachmentId")
        filename  = payload.get("filename", "")
        size      = payload.get("body", {}).get("size", 0)

        if att_id and filename:
            attachments.append({
                "name":          filename,
                "mime_type":     mime,
                "size_bytes":    size,
                "attachment_id": att_id,
            })
        elif mime == "text/plain" and body_data:
            body_text = _decode_b64(body_data)
        return body_text, attachments

    for part in parts:
        part_mime = part.get("mimeType", "")
        sub_body, sub_att = _extract_body_and_attachments(part)
        attachments.extend(sub_att)

        # Prefer text/plain; only fall back to html-stripped if nothing yet
        if part_mime == "text/plain" and sub_body and not body_text:
            body_text = sub_body
        elif part_mime == "text/html" and sub_body and not body_text:
            # Strip HTML tags for plain text fallback
            body_text = re.sub(r"<[^>]+>", " ", sub_body)
            body_text = re.sub(r"\s+", " ", body_text).strip()

    return body_text, attachments


# ── EmailCache ──────────────────────────────────────────────────────

class EmailCache:
    """
    Manages local JSON email cache.

    Usage:
        cache = EmailCache()
        emails = cache.load()             # load from disk (may be empty)
        cache.save(emails)                # write to disk
        cache.is_stale()                  # True if cache is older than CACHE_DAYS
        cache.merge(new_emails)           # add new emails, deduplicate by id
        cache.update_categories(mapping)  # write {id: category} back to cache
    """

    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)

    # ── IO ──────────────────────────────────────────────────────────
    def load(self) -> list:
        """Load emails from cache. Returns empty list if file missing."""
        if not os.path.exists(CACHE_FILE):
            return []
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[EmailCache] Loaded {len(data)} emails from cache.")
            return data
        except Exception as e:
            print(f"[EmailCache] Failed to load cache: {e}")
            return []

    def save(self, emails: list) -> None:
        """Write emails list to cache JSON."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(emails, f, indent=2, ensure_ascii=False)
            print(f"[EmailCache] Saved {len(emails)} emails to cache.")
        except Exception as e:
            print(f"[EmailCache] Failed to save cache: {e}")

    # ── Staleness ───────────────────────────────────────────────────
    def is_stale(self) -> bool:
        """
        Returns True if:
        - Cache file does not exist, OR
        - Newest email in cache is older than CACHE_DAYS
        """
        if not os.path.exists(CACHE_FILE):
            return True
        emails = self.load()
        if not emails:
            return True

        now_ts = datetime.now(timezone.utc).timestamp()
        newest_ts = max(e.get("timestamp_unix", 0) for e in emails)
        age_days = (now_ts - newest_ts) / 86400
        stale = age_days > CACHE_DAYS
        print(f"[EmailCache] Newest email age: {age_days:.1f} days – stale={stale}")
        return stale

    def last_updated_str(self) -> str:
        """Human-readable string of when the cache was last written."""
        if not os.path.exists(CACHE_FILE):
            return "Never"
        mtime = os.path.getmtime(CACHE_FILE)
        dt = datetime.fromtimestamp(mtime)
        return dt.strftime("%d %b %Y, %H:%M:%S")

    def cache_stats(self) -> dict:
        """Return summary stats about the cache."""
        emails = self.load()
        if not emails:
            return {"total": 0, "last_updated": "Never", "date_range": "N/A"}
        total = len(emails)
        last_upd = self.last_updated_str()
        dates = sorted([e.get("date_iso", "") for e in emails if e.get("date_iso")])
        date_range = f"{dates[0][:10]} → {dates[-1][:10]}" if dates else "N/A"
        return {"total": total, "last_updated": last_upd, "date_range": date_range}

    # ── Merge ───────────────────────────────────────────────────────
    def merge(self, new_emails: list) -> list:
        """
        Merge new_emails into existing cache, deduplicating by email id.
        Prunes emails older than CACHE_DAYS. Returns the merged list.
        """
        existing  = self.load()
        by_id     = {e["id"]: e for e in existing}

        for email in new_emails:
            eid = email.get("id")
            if eid:
                # Preserve existing category if already classified
                if eid in by_id and by_id[eid].get("category"):
                    email.setdefault("category", by_id[eid]["category"])
                by_id[eid] = email

        # Prune older than CACHE_DAYS
        cutoff = datetime.now(timezone.utc).timestamp() - (CACHE_DAYS * 86400)
        merged = [
            e for e in by_id.values()
            if e.get("timestamp_unix", 0) >= cutoff
        ]
        merged.sort(key=lambda e: e.get("timestamp_unix", 0), reverse=True)
        return merged

    # ── Category update ─────────────────────────────────────────────
    def update_categories(self, categories: dict) -> None:
        """
        Write classification results back to the cache.
        categories: {email_id: category_string}
        """
        emails = self.load()
        updated = 0
        for email in emails:
            eid = email.get("id")
            if eid and eid in categories:
                email["category"] = categories[eid]
                updated += 1
        self.save(emails)
        print(f"[EmailCache] Updated categories for {updated} emails.")


# ── Gmail → Rich Email Dict ──────────────────────────────────────────

def build_email_record(msg_data: dict, account_id: str = "default") -> dict:
    """
    Convert a raw Gmail API message (format=full) into our rich cache record.
    """
    payload  = msg_data.get("payload", {})
    headers  = {h["name"]: h["value"] for h in payload.get("headers", [])}

    sender_full  = headers.get("From", "Unknown")
    sender_email = re.findall(r"[\w.+-]+@[\w.-]+", sender_full)
    sender_email = sender_email[0] if sender_email else sender_full

    date_raw  = headers.get("Date", "")
    date_iso, ts_unix = _parse_date_to_iso(date_raw)

    body_text, attachments = _extract_body_and_attachments(payload)

    return {
        "id":            msg_data.get("id", ""),
        "thread_id":     msg_data.get("threadId", ""),
        "account_id":    account_id,
        "subject":       headers.get("Subject", "No Subject"),
        "sender":        sender_full,
        "sender_email":  sender_email,
        "date_raw":      date_raw,
        "date_iso":      date_iso,
        "timestamp_unix": ts_unix,
        "snippet":       msg_data.get("snippet", ""),
        "body":          body_text.strip() or msg_data.get("snippet", ""),
        "has_attachments": len(attachments) > 0,
        "attachments":   attachments,
        "labels":        msg_data.get("labelIds", []),
        "category":      None,           # filled later by classify node
        "cached_at":     datetime.now(timezone.utc).isoformat(),
    }
