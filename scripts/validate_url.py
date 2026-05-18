"""URL validation with SSRF protection for Three-O platform."""

import argparse
import ipaddress
import json
import re
import socket
import sys
from typing import Any, Dict
from urllib.parse import urlparse


BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

ALLOWED_SCHEMES = {"http", "https"}
MAX_URL_LENGTH = 2048


def validate_url(url: str) -> Dict[str, Any]:
    """Validate URL for safety and correctness. Returns dict with 'valid' bool and 'error' if invalid."""
    if not url:
        return {"valid": False, "error": "Empty URL"}

    if len(url) > MAX_URL_LENGTH:
        return {"valid": False, "error": f"URL exceeds {MAX_URL_LENGTH} characters"}

    try:
        parsed = urlparse(url)
    except Exception as e:
        return {"valid": False, "error": f"Parse error: {e}"}

    if parsed.scheme not in ALLOWED_SCHEMES:
        return {"valid": False, "error": f"Scheme '{parsed.scheme}' not allowed. Use http or https."}

    if not parsed.hostname:
        return {"valid": False, "error": "No hostname found"}

    hostname = parsed.hostname

    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        try:
            ip = ipaddress.ip_address(hostname)
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return {"valid": False, "error": f"IP {hostname} is in blocked network {network}"}
        except ValueError:
            return {"valid": False, "error": f"Invalid IP address: {hostname}"}
    else:
        try:
            resolved = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved)
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return {"valid": False, "error": f"Hostname {hostname} resolves to blocked IP {resolved}"}
        except socket.gaierror:
            return {"valid": False, "error": f"Cannot resolve hostname: {hostname}"}

    return {"valid": True, "url": url, "hostname": hostname, "scheme": parsed.scheme}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate URL for SSRF protection")
    parser.add_argument("url", help="URL to validate")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = validate_url(args.url)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["valid"]:
            print(f"✓ Valid: {result['url']}")
        else:
            print(f"✗ Invalid: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
