"""CWV terminology validator. Ensures INP is used, never FID."""

import argparse
import re
import sys


FID_PATTERN = re.compile(r'\bFID\b')
ALLOWED_FID_CONTEXTS = [
    r'never\s+FID',
    r'not\s+FID',
    r'INP.*not.*FID',
    r'INP.*never.*FID',
    r'deprecated.*FID',
    r'FID.*deprecated',
    r'replaced.*FID',
    r'FID.*replaced',
]


def check_cwv_terminology(filepath: str) -> list:
    """Check for incorrect FID usage in file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        return []

    violations = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
            continue
        if not FID_PATTERN.search(line):
            continue

        is_allowed = any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in ALLOWED_FID_CONTEXTS
        )

        if not is_allowed:
            violations.append({
                "line": line_num,
                "text": line.strip(),
                "message": "FID reference found — must use INP (Interaction to Next Paint). FID deprecated March 2024.",
            })

    return violations


def main():
    parser = argparse.ArgumentParser(description="CWV terminology check (INP not FID)")
    parser.add_argument("--file", required=True, help="File to check")
    args = parser.parse_args()

    violations = check_cwv_terminology(args.file)

    if not violations:
        sys.exit(0)

    for v in violations:
        print(f"[ERROR] Line {v['line']}: {v['message']}")
        print(f"  → {v['text']}")

    sys.exit(1)


if __name__ == "__main__":
    main()
