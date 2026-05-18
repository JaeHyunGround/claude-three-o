"""Three-O configuration management. Loads API keys and settings from ~/.config/three-o/."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_DIR = Path.home() / ".config" / "three-o"
KEYS = {
    "openai": "openai_key.txt",
    "perplexity": "perplexity_key.txt",
    "google": "google_api_key.txt",
    "anthropic": "anthropic_key.txt",
    "naver_client_id": "naver_api.json",
    "dataforseo": "dataforseo_key.txt",
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key(service: str) -> Optional[str]:
    key_file = CONFIG_DIR / KEYS.get(service, f"{service}_key.txt")
    if not key_file.exists():
        return None
    content = key_file.read_text().strip()
    if service == "naver_client_id":
        data = json.loads(content)
        return str(data.get("client_id", ""))
    return content


def get_naver_credentials() -> Optional[Dict[str, str]]:
    key_file = CONFIG_DIR / "naver_api.json"
    if not key_file.exists():
        return None
    result: Dict[str, str] = json.loads(key_file.read_text())
    return result


def list_configured_services() -> List[str]:
    configured = []
    for service, filename in KEYS.items():
        if (CONFIG_DIR / filename).exists():
            configured.append(service)
    return configured


def get_db_path() -> Path:
    db_dir = CONFIG_DIR / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "three_o.db"


def get_reports_dir() -> Path:
    reports = Path.cwd() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def main():
    parser = argparse.ArgumentParser(description="Three-O configuration utility")
    parser.add_argument("action", choices=["check", "path", "services"], help="Action to perform")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.action == "check":
        services = list_configured_services()
        missing = [s for s in KEYS if s not in services]
        result = {"configured": services, "missing": missing}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Configured: {', '.join(services) or 'none'}")
            print(f"Missing: {', '.join(missing) or 'none'}")

    elif args.action == "path":
        result = {"config_dir": str(CONFIG_DIR), "db_path": str(get_db_path())}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Config dir: {CONFIG_DIR}")
            print(f"DB path: {get_db_path()}")

    elif args.action == "services":
        result = {"services": list(KEYS.keys()), "files": KEYS}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for service, filename in KEYS.items():
                status = "✓" if (CONFIG_DIR / filename).exists() else "✗"
                print(f"  {status} {service}: {CONFIG_DIR / filename}")


if __name__ == "__main__":
    main()
