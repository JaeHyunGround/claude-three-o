"""Schema recommendation validator for Three-O platform."""

import argparse
import re
import sys


DEPRECATED_SCHEMAS = {
    "HowTo": {
        "deprecated": "September 2023",
        "message": "HowTo schema is deprecated. Google no longer shows HowTo rich results.",
        "severity": "error",
    },
}

RESTRICTED_SCHEMAS = {
    "FAQPage": {
        "restriction": "Government and healthcare sites only",
        "since": "August 2023",
        "message": "FAQPage schema is restricted to government (.go.kr, .gov) and healthcare sites only since August 2023.",
        "severity": "warning",
        "allowed_domains": [".go.kr", ".gov", ".gov.kr", ".mil", ".edu"],
        "allowed_industries": ["healthcare", "clinic", "hospital", "government"],
    },
}


def check_schema_recommendations(filepath: str) -> list:
    """Check for deprecated or restricted schema recommendations."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        return []

    violations = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith("#"):
            continue

        for schema_type, info in DEPRECATED_SCHEMAS.items():
            if schema_type in line:
                context = "\n".join(lines[max(0, line_num - 3):line_num + 3])
                if re.search(r'(deprecated|removed|do not|never|금지)', context, re.IGNORECASE):
                    continue

                violations.append({
                    "line": line_num,
                    "schema": schema_type,
                    "severity": info["severity"],
                    "message": info["message"],
                })

        for schema_type, info in RESTRICTED_SCHEMAS.items():
            if schema_type in line:
                context = "\n".join(lines[max(0, line_num - 3):line_num + 3])
                if re.search(r'(restricted|only|government|healthcare|정부|의료)', context, re.IGNORECASE):
                    continue

                violations.append({
                    "line": line_num,
                    "schema": schema_type,
                    "severity": info["severity"],
                    "message": info["message"],
                })

    return violations


def validate_schema_template(schema_json: str) -> list:
    """Validate a schema JSON template against rules."""
    issues = []

    try:
        import json
        data = json.loads(schema_json)
    except (json.JSONDecodeError, TypeError):
        return issues

    schema_type = data.get("@type", "")
    if isinstance(schema_type, list):
        types = schema_type
    else:
        types = [schema_type]

    for t in types:
        if t in DEPRECATED_SCHEMAS:
            issues.append({
                "schema": t,
                "severity": "error",
                "message": DEPRECATED_SCHEMAS[t]["message"],
            })
        if t in RESTRICTED_SCHEMAS:
            issues.append({
                "schema": t,
                "severity": "warning",
                "message": RESTRICTED_SCHEMAS[t]["message"],
            })

    return issues


def main():
    parser = argparse.ArgumentParser(description="Schema recommendation validator")
    parser.add_argument("--file", help="File to check")
    parser.add_argument("--schema", help="Schema JSON string to validate")
    args = parser.parse_args()

    if args.file:
        violations = check_schema_recommendations(args.file)
    elif args.schema:
        violations = validate_schema_template(args.schema)
    else:
        print("Error: Provide --file or --schema", file=sys.stderr)
        sys.exit(1)

    if not violations:
        sys.exit(0)

    has_errors = False
    for v in violations:
        prefix = "ERROR" if v["severity"] == "error" else "WARN"
        line_info = f" (line {v['line']})" if "line" in v else ""
        print(f"[{prefix}]{line_info} {v['schema']}: {v['message']}")
        if v["severity"] == "error":
            has_errors = True

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
