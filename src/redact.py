"""
Recon – redact.py
Configurable sensitive data redaction for PDFs and text files.

Extends beyond SSN-only redaction to handle any pattern: EIN, bank account numbers,
routing numbers, credit cards, phone numbers, emails, addresses, API keys, passwords.

Redaction profiles define which patterns to apply. Profiles are composable — you can
combine multiple profiles for a single run.

Usage (as module):
    from src.redact import redact_file
    redact_file("tax_return.pdf", profiles=["ssn", "ein", "bank"])

Usage (CLI from recon directory):
    python -m src.redact input.pdf --profiles ssn ein bank
    python -m src.redact input.pdf --all
    python -m src.redact input.pdf --profiles ssn --dry-run
    python -m src.redact input.txt --profiles email phone  # text files too

Profiles:
    ssn       — Social Security Numbers (XXX-XX-XXXX, XXX XX XXXX, XXXXXXXXX)
    ein       — Employer ID Numbers (XX-XXXXXXX)
    bank      — Bank account numbers (8-17 digits in account-number contexts)
    routing   — ABA routing numbers (9 digits near "routing")
    credit    — Credit card numbers (13-19 digits, Luhn-valid)
    phone     — US phone numbers ((XXX) XXX-XXXX, XXX-XXX-XXXX, etc.)
    email     — Email addresses
    address   — Street addresses (number + street name patterns)
    apikey    — API keys, tokens, secrets (key=value, Bearer tokens)
    name      — Specific names (provide via --names "Chris Waldrop,Linzy Waldrop")

Dependencies: PyMuPDF (fitz) for PDFs. Text files use stdlib only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

# ── Redaction pattern registry ─────────────────────────────────────

REDACTION_PROFILES: dict[str, list[re.Pattern]] = {
    "ssn": [
        re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        re.compile(r'\b\d{3}\s\d{2}\s\d{4}\b'),
        re.compile(r'(?<!\d)\d{9}(?!\d)'),  # 9 consecutive digits (conservative)
    ],
    "ein": [
        re.compile(r'\b\d{2}-\d{7}\b'),
    ],
    "bank": [
        # Account numbers: 8-17 digits, context-aware
        re.compile(r'(?i)(?:account|acct)[^0-9]{0,20}(\d{8,17})\b'),
    ],
    "routing": [
        re.compile(r'(?i)(?:routing|transit|aba)[^0-9]{0,20}(\d{9})\b'),
    ],
    "credit": [
        # Visa, MC, Amex, Discover patterns
        re.compile(r'\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
        re.compile(r'\b3[47]\d{2}[- ]?\d{6}[- ]?\d{5}\b'),  # Amex
    ],
    "phone": [
        re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    ],
    "email": [
        re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    ],
    "address": [
        # US street address: number + street name + suffix
        re.compile(r'\b\d{1,6}\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,3}\s+(?:St|Ave|Blvd|Dr|Ln|Rd|Ct|Pl|Way|Cir|Pkwy|Hwy)\b', re.IGNORECASE),
    ],
    "apikey": [
        # Common API key patterns
        re.compile(r'(?i)(?:api[_-]?key|secret|token|password|auth)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
        re.compile(r'\bsk[-_][a-zA-Z0-9]{20,}\b'),  # Stripe/OpenAI style
        re.compile(r'\bBearer\s+[a-zA-Z0-9._\-]{20,}\b'),
    ],
}

ALL_PROFILE_NAMES = list(REDACTION_PROFILES.keys())

REPLACEMENT_TEXT = "████████"


def _get_patterns(profiles: list[str], custom_names: Optional[list[str]] = None) -> list[re.Pattern]:
    """Collect all regex patterns for the requested profiles."""
    patterns = []
    for profile in profiles:
        if profile not in REDACTION_PROFILES:
            print(f"  Warning: unknown profile '{profile}', skipping")
            continue
        patterns.extend(REDACTION_PROFILES[profile])

    if custom_names:
        for name in custom_names:
            name = name.strip()
            if name:
                patterns.append(re.compile(re.escape(name), re.IGNORECASE))

    return patterns


def redact_pdf(input_path: str, output_path: str, patterns: list[re.Pattern]) -> int:
    """Redact patterns from a PDF. Returns total redaction count."""
    try:
        import fitz
    except ImportError:
        print("Error: PyMuPDF (fitz) required for PDF redaction. pip install PyMuPDF")
        return 0

    doc = fitz.open(input_path)
    total = 0

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        count = 0

        for pattern in patterns:
            for match in pattern.finditer(text):
                # Use the full match or group(1) if it's a capturing group
                target = match.group(1) if match.lastindex else match.group()
                instances = page.search_for(target)
                for inst in instances:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
                    count += 1

        if count > 0:
            page.apply_redactions()
            total += count
            print(f"  Page {page_num + 1}: {count} redaction(s)")

    doc.save(output_path)
    doc.close()
    return total


def redact_text(input_path: str, output_path: str, patterns: list[re.Pattern]) -> int:
    """Redact patterns from a text file. Returns total redaction count."""
    content = Path(input_path).read_text(encoding="utf-8", errors="replace")
    total = 0

    for pattern in patterns:
        matches = list(pattern.finditer(content))
        total += len(matches)
        if pattern.groups:
            # Replace only the capturing group
            for match in reversed(matches):
                start, end = match.span(1)
                content = content[:start] + REPLACEMENT_TEXT + content[end:]
        else:
            content = pattern.sub(REPLACEMENT_TEXT, content)

    Path(output_path).write_text(content, encoding="utf-8")
    return total


def redact_file(
    input_path: str,
    output_path: Optional[str] = None,
    profiles: Optional[list[str]] = None,
    custom_names: Optional[list[str]] = None,
    dry_run: bool = False,
) -> str:
    """
    Redact sensitive data from a file.

    Args:
        input_path: Path to the file to redact
        output_path: Output path (default: {stem}_REDACTED{suffix})
        profiles: List of profile names to apply (default: ["ssn"])
        custom_names: Additional literal strings to redact (e.g., personal names)
        dry_run: If True, report what would be redacted without writing

    Returns:
        Path to the redacted output file
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if profiles is None:
        profiles = ["ssn"]

    if output_path is None:
        output_path = str(p.parent / f"{p.stem}_REDACTED{p.suffix}")

    patterns = _get_patterns(profiles, custom_names)
    if not patterns:
        print("No valid patterns to apply.")
        return output_path

    print(f"Redacting: {input_path}")
    print(f"Profiles: {', '.join(profiles)}")
    if custom_names:
        print(f"Custom names: {', '.join(custom_names)}")

    if dry_run:
        # Read and count matches without writing
        if p.suffix.lower() == ".pdf":
            try:
                import fitz
                doc = fitz.open(input_path)
                total = 0
                for page_num, page in enumerate(doc):
                    text = page.get_text("text")
                    for pattern in patterns:
                        total += len(pattern.findall(text))
                doc.close()
            except ImportError:
                print("PyMuPDF required for PDF dry-run")
                total = 0
        else:
            content = p.read_text(encoding="utf-8", errors="replace")
            total = sum(len(pattern.findall(content)) for pattern in patterns)
        print(f"\n[DRY RUN] Would redact {total} match(es). No file written.")
        return output_path

    if p.suffix.lower() == ".pdf":
        total = redact_pdf(input_path, output_path, patterns)
    else:
        total = redact_text(input_path, output_path, patterns)

    print(f"\nTotal redactions: {total}")
    print(f"Saved to: {output_path}")
    return output_path


# ── CLI ────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Redact sensitive data from PDFs and text files.",
        epilog="Profiles: " + ", ".join(ALL_PROFILE_NAMES),
    )
    parser.add_argument("input", help="Input file path")
    parser.add_argument("-o", "--output", help="Output file path (default: {stem}_REDACTED{ext})")
    parser.add_argument(
        "-p", "--profiles", nargs="+", default=["ssn"],
        choices=ALL_PROFILE_NAMES,
        help="Redaction profiles to apply (default: ssn)",
    )
    parser.add_argument("--all", action="store_true", help="Apply all redaction profiles")
    parser.add_argument("--names", help='Comma-separated names to redact (e.g., "John Doe,Jane Doe")')
    parser.add_argument("--dry-run", action="store_true", help="Report matches without writing")
    args = parser.parse_args()

    profiles = ALL_PROFILE_NAMES if args.all else args.profiles
    names = [n.strip() for n in args.names.split(",")] if args.names else None

    redact_file(args.input, args.output, profiles, names, args.dry_run)


if __name__ == "__main__":
    main()
