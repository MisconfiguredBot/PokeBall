#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import time
from pathlib import Path


DEFAULT_LOG_PATHS = (
    "/home/cowrie/cowrie/var/log/cowrie/cowrie.json",
    "/opt/cowrie/var/log/cowrie/cowrie.json",
    "/home/cowrie/cowrie/var/log/cowrie/cowrie.log",
    "/opt/cowrie/var/log/cowrie/cowrie.log",
)
DEFAULT_OUTPUT_PATH = "pokeball_log.txt"

JSON_IP_FIELDS = ("src_ip", "source_ip", "ip", "peerIP", "peer_ip")
TEXT_IP_PATTERNS = (
    re.compile(r"\bSRC=([0-9a-fA-F:.]+)\b"),
    re.compile(r"\b([0-9]{1,3}(?:\.[0-9]{1,3}){3})\b"),
    re.compile(r"\b([0-9a-fA-F:]+:[0-9a-fA-F:.]+)\b"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract unique client IPs from Cowrie logs and write them to pokeball_log.txt."
    )
    parser.add_argument(
        "--log",
        dest="log_path",
        help="Path to a Cowrie log file. If omitted, common locations are tried automatically.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output file for unique IPs (default: {DEFAULT_OUTPUT_PATH}).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds to wait between checks for new log lines (default: 1.0).",
    )
    return parser.parse_args()


def pick_log_path(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Log file not found: {path}")
        return path

    for candidate in DEFAULT_LOG_PATHS:
        path = Path(candidate)
        if path.is_file():
            return path

    searched = "\n".join(f"  - {path}" for path in DEFAULT_LOG_PATHS)
    raise FileNotFoundError(
        "Could not find a Cowrie log file automatically. Checked:\n" + searched
    )


def is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def extract_ip(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None

    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for field in JSON_IP_FIELDS:
                value = payload.get(field)
                if isinstance(value, str) and is_valid_ip(value):
                    return value

    for pattern in TEXT_IP_PATTERNS:
        match = pattern.search(stripped)
        if not match:
            continue
        value = match.group(1)
        if is_valid_ip(value):
            return value

    return None


def load_known_ips(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()

    known_ips: set[str] = set()
    with output_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if is_valid_ip(value):
                known_ips.add(value)
    return known_ips


def append_ip(output_path: Path, ip: str) -> None:
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{ip}\n")


def process_line(line: str, known_ips: set[str], output_path: Path) -> None:
    ip = extract_ip(line)
    if not ip or ip in known_ips:
        return

    append_ip(output_path, ip)
    known_ips.add(ip)
    print(f"[+] saved {ip}", flush=True)


def follow_file(log_path: Path, known_ips: set[str], output_path: Path, poll_interval: float) -> None:
    inode = None
    handle = None

    while True:
        if handle is None:
            handle = log_path.open("r", encoding="utf-8", errors="replace")
            inode = os.fstat(handle.fileno()).st_ino

            for line in handle:
                process_line(line, known_ips, output_path)

        line = handle.readline()
        if line:
            process_line(line, known_ips, output_path)
            continue

        try:
            current_inode = log_path.stat().st_ino
        except FileNotFoundError:
            current_inode = None

        if current_inode != inode:
            handle.close()
            handle = None
            time.sleep(poll_interval)
            continue

        time.sleep(poll_interval)


def main() -> int:
    args = parse_args()

    try:
        log_path = pick_log_path(args.log_path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    known_ips = load_known_ips(output_path)

    print(f"Watching: {log_path}")
    print(f"Writing unique IPs to: {output_path}")
    print(f"Already known: {len(known_ips)}")

    try:
        follow_file(log_path, known_ips, output_path, args.poll_interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
