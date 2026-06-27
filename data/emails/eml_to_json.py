#!/usr/bin/env python3
"""Parse RFC 5322/MIME .eml files into a deterministic JSON array.

The output schema is compatible with the source emails.json file:
id, from, to, subject, body, received_at, labels.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        type=Path,
        nargs="+",
        help="One or more .eml files or directories containing .eml files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this file; stdout is used when omitted",
    )
    parser.add_argument(
        "--timezone",
        default="Europe/Paris",
        help="Timezone used for received_at (default: Europe/Paris)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Maximum size of each .eml file (default: {DEFAULT_MAX_BYTES})",
    )
    return parser.parse_args()


def discover_eml_files(inputs: list[Path]) -> list[Path]:
    """Return unique files in a stable, platform-independent order."""
    discovered: dict[str, Path] = {}
    for input_path in inputs:
        if input_path.is_file():
            if input_path.suffix.lower() != ".eml":
                raise ValueError(f"Not an .eml file: {input_path}")
            candidates = [input_path]
        elif input_path.is_dir():
            candidates = [path for path in input_path.rglob("*") if path.is_file() and path.suffix.lower() == ".eml"]
        else:
            raise ValueError(f"Input does not exist: {input_path}")

        for candidate in candidates:
            resolved = candidate.resolve()
            discovered[resolved.as_posix()] = resolved

    files = [discovered[key] for key in sorted(discovered)]
    if not files:
        raise ValueError("No .eml files found")
    return files


def read_message(path: Path, max_bytes: int) -> EmailMessage:
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"File exceeds --max-bytes ({size} bytes): {path}")
    parsed = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if not isinstance(parsed, EmailMessage):
        raise ValueError(f"Could not parse MIME message: {path}")
    return parsed


def require_header(message: Message, name: str, path: Path) -> str:
    value = message.get(name)
    if value is None or not str(value).strip():
        raise ValueError(f"Missing {name} header: {path}")
    return str(value).strip()


def normalize_addresses(raw_values: list[str], header: str, path: Path) -> str:
    addresses = getaddresses(raw_values)
    if not addresses or any(not address for _, address in addresses):
        raise ValueError(f"Invalid {header} header: {path}")
    return ", ".join(f"{name} <{address}>" if name else address for name, address in addresses)


def extract_id(message: Message, path: Path) -> str:
    source_id = message.get("X-Source-ID")
    if source_id and str(source_id).strip():
        return str(source_id).strip()

    message_id = message.get("Message-ID")
    if message_id:
        local_part = str(message_id).strip().strip("<>").split("@", 1)[0]
        if local_part:
            return local_part.upper()
    return path.stem


def extract_received_at(message: Message, timezone: ZoneInfo, path: Path) -> str:
    raw_date = require_header(message, "Date", path)
    try:
        parsed = parsedate_to_datetime(raw_date)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Date header in {path}: {raw_date!r}") from exc
    if parsed is None:
        raise ValueError(f"Invalid Date header in {path}: {raw_date!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone).replace(tzinfo=None).isoformat(timespec="seconds")


def decode_text_part(part: Message, path: Path) -> str:
    try:
        content = part.get_content()
    except (LookupError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot decode text body in {path}") from exc
    if not isinstance(content, str):
        raise ValueError(f"Text body is not textual in {path}")
    return content.replace("\r\n", "\n").rstrip("\n")


def extract_body(message: EmailMessage, path: Path) -> str:
    """Prefer the first non-attachment text/plain body, then text/html."""
    if not message.is_multipart():
        return decode_text_part(message, path)

    plain_parts: list[Message] = []
    html_parts: list[Message] = []
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        if part.get_content_type() == "text/plain":
            plain_parts.append(part)
        elif part.get_content_type() == "text/html":
            html_parts.append(part)

    candidates = plain_parts or html_parts
    if not candidates:
        raise ValueError(f"No text/plain or text/html body found: {path}")
    return "\n".join(decode_text_part(part, path) for part in candidates)


def extract_labels(message: Message) -> list[str]:
    raw = message.get("X-Labels") or message.get("Keywords")
    if not raw:
        return []
    labels = [label.strip() for label in str(raw).split(",") if label.strip()]
    return list(dict.fromkeys(labels))


def parse_email(path: Path, timezone: ZoneInfo, max_bytes: int) -> dict:
    message = read_message(path, max_bytes)
    from_values = message.get_all("From", [])
    to_values = message.get_all("To", [])
    if not from_values:
        raise ValueError(f"Missing From header: {path}")
    if not to_values:
        raise ValueError(f"Missing To header: {path}")

    return {
        "id": extract_id(message, path),
        "from": normalize_addresses([str(value) for value in from_values], "From", path),
        "to": normalize_addresses([str(value) for value in to_values], "To", path),
        "subject": require_header(message, "Subject", path),
        "body": extract_body(message, path),
        "received_at": extract_received_at(message, timezone, path),
        "labels": extract_labels(message),
    }


def serialize(records: list[dict]) -> str:
    records.sort(key=lambda record: (record["id"].casefold(), record["received_at"]))
    return json.dumps(records, ensure_ascii=False, indent=2) + "\n"


# Dossier par défaut des .eml bruts (source de vérité des emails).
DEFAULT_RAW_DIR = Path(__file__).resolve().parent / "raw"


def load_emails(
    raw_dir: Path | str | None = None,
    timezone: str = "Europe/Paris",
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> list[dict]:
    """API publique : parse tous les .eml d'un dossier et renvoie la liste d'emails.

    Sortie identique à l'ancien emails.json (id, from, to, subject, body,
    received_at, labels), triée par (id, received_at). C'est LE point d'entrée
    pour validate.py, le mock MCP email et seed_outlook — il n'y a plus de
    emails.json sur disque : les .eml bruts sont la source de vérité.
    """
    directory = Path(raw_dir) if raw_dir is not None else DEFAULT_RAW_DIR
    tz = ZoneInfo(timezone)
    files = discover_eml_files([directory])
    records = [parse_email(path, tz, max_bytes) for path in files]
    ids = [r["id"] for r in records]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"Duplicate email ids: {', '.join(duplicates)}")
    records.sort(key=lambda r: (r["id"].casefold(), r["received_at"]))
    return records


def main() -> int:
    args = parse_args()
    try:
        if args.max_bytes <= 0:
            raise ValueError("--max-bytes must be greater than zero")
        timezone = ZoneInfo(args.timezone)
        files = discover_eml_files(args.inputs)
        records = [parse_email(path, timezone, args.max_bytes) for path in files]

        ids = [record["id"] for record in records]
        duplicate_ids = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
        if duplicate_ids:
            raise ValueError(f"Duplicate email ids: {', '.join(duplicate_ids)}")

        output = serialize(records)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8", newline="\n")
            print(f"Parsed {len(records)} email(s) into {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(output)
        return 0
    except (OSError, ValueError, ZoneInfoNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
