"""Three-O quality gate validator. Checks outputs against quality rules."""

import argparse
import re
import sys


QUALITY_RULES = [
    {
        "id": "cwv-inp-not-fid",
        "description": "Core Web Vitals must use INP, never FID",
        "pattern": r'\bFID\b',
        "severity": "error",
        "message": "Found 'FID' reference — use INP (Interaction to Next Paint) instead. FID was deprecated March 2024.",
    },
    {
        "id": "no-howto-schema",
        "description": "HowTo schema deprecated Sept 2023",
        "pattern": r'HowTo',
        "context_pattern": r'(schema|structured.?data|json.?ld|@type)',
        "severity": "error",
        "message": "HowTo schema is deprecated (Sept 2023). Do not recommend HowTo structured data.",
    },
    {
        "id": "faq-schema-restriction",
        "description": "FAQ schema restricted to gov/health Aug 2023",
        "pattern": r'FAQPage',
        "context_pattern": r'(schema|structured.?data|json.?ld|@type)',
        "severity": "warning",
        "message": "FAQ schema (FAQPage) is restricted to government and healthcare sites only (Aug 2023).",
    },
    {
        "id": "no-hardcoded-paths",
        "description": "No hardcoded config paths",
        "pattern": r'(?<!//)(?<!\")(/Users/|/home/|C:\\\\)',
        "severity": "warning",
        "message": "Hardcoded path detected. Use os.path or config module instead.",
    },
    {
        "id": "no-api-keys-in-code",
        "description": "No API keys in source",
        "pattern": r'(sk-[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9_-]{35})',
        "severity": "error",
        "message": "Possible API key detected in source code. Store in config, not in code.",
    },
    {
        "id": "korean-char-awareness",
        "description": "Korean content must consider character vs byte length",
        "pattern": r'len\([^)]*\)\s*>\s*(60|160)\b',
        "context_pattern": r'(title|description|메타|meta)',
        "severity": "info",
        "message": "Length check detected — ensure Korean character counting is used (not byte length) for titles (30 chars) and descriptions (80 chars).",
    },
]


def validate_file(filepath: str) -> list:
    """Validate a file against quality rules."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        return []

    violations = []
    lines = content.split("\n")

    for rule in QUALITY_RULES:
        pattern = re.compile(rule["pattern"], re.IGNORECASE)

        for line_num, line in enumerate(lines, 1):
            if line.strip().startswith("#") or line.strip().startswith('"""'):
                continue

            match = pattern.search(line)
            if not match:
                continue

            if rule.get("context_pattern"):
                context_window = "\n".join(lines[max(0, line_num - 5):line_num + 5])
                if not re.search(rule["context_pattern"], context_window, re.IGNORECASE):
                    continue

            violations.append({
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "line": line_num,
                "message": rule["message"],
                "matched": match.group(0),
            })

    return violations


def main():
    parser = argparse.ArgumentParser(description="Three-O quality gate validator")
    parser.add_argument("--file", required=True, help="File to validate")
    args = parser.parse_args()

    violations = validate_file(args.file)

    if not violations:
        sys.exit(0)

    has_errors = False
    for v in violations:
        prefix = "ERROR" if v["severity"] == "error" else "WARN" if v["severity"] == "warning" else "INFO"
        print(f"[{prefix}] Line {v['line']}: {v['message']} (matched: '{v['matched']}')")
        if v["severity"] == "error":
            has_errors = True

    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
