"""Plant or verify the VP-2 Twilio API credential acorn without echoing values."""

from __future__ import annotations

import argparse
import getpass
import os
import stat
import subprocess
import tempfile
from pathlib import Path

DEFAULT_TARGET = Path.home() / ".novacore" / "secrets" / "vp2-twilio.env"
REQUIRED = ("TWILIO_ACCOUNT_SID", "TWILIO_API_KEY", "TWILIO_API_SECRET")


def parse_env(text: str) -> tuple[list[str], dict[str, str]]:
    lines = text.splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return lines, values


def validate(values: dict[str, str]) -> None:
    if not values["TWILIO_ACCOUNT_SID"].startswith("AC"):
        raise ValueError("TWILIO_ACCOUNT_SID must start with AC")
    if not values["TWILIO_API_KEY"].startswith("SK"):
        raise ValueError("TWILIO_API_KEY must start with SK")
    if len(values["TWILIO_API_SECRET"]) < 16:
        raise ValueError("TWILIO_API_SECRET is unexpectedly short")
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ValueError("credential values cannot contain newlines")


def render(existing_lines: list[str], values: dict[str, str]) -> str:
    remaining = dict(values)
    output: list[str] = []
    for line in existing_lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}")
                continue
        output.append(line)
    if output and output[-1] != "":
        output.append("")
    if remaining:
        output.append("# VP-2 Twilio API acorn (values never enter chat/DB/Git)")
        output.extend(f"{key}={remaining[key]}" for key in REQUIRED if key in remaining)
    return "\n".join(output).rstrip() + "\n"


def lock_down_windows(path: Path) -> None:
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return
    user = os.environ.get("USERNAME")
    if not user:
        raise RuntimeError("USERNAME is unavailable for ACL lockdown")
    result = subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(F)"],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError("Windows ACL lockdown failed")


def plant(target: Path, values: dict[str, str], *, lock_acl: bool = True) -> None:
    validate(values)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    lines, _ = parse_env(existing)
    content = render(lines, values)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        Path(temp_name).replace(target)
        if lock_acl:
            lock_down_windows(target)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def presence(target: Path) -> dict[str, bool]:
    if not target.is_file():
        return {key: False for key in REQUIRED}
    _, values = parse_env(target.read_text(encoding="utf-8"))
    return {key: bool(values.get(key)) for key in REQUIRED}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        state = presence(args.target)
        for key in REQUIRED:
            print(f"{key}={'PRESENT' if state[key] else 'MISSING'}")
        raise SystemExit(0 if all(state.values()) else 2)

    print(f"VP-2 Twilio acorn destination: {args.target}")
    print("Values are entered locally with hidden input and are never printed.")
    values = {
        "TWILIO_ACCOUNT_SID": getpass.getpass("Twilio Account SID (AC...): ").strip(),
        "TWILIO_API_KEY": getpass.getpass("Twilio Standard API Key SID (SK...): ").strip(),
        "TWILIO_API_SECRET": getpass.getpass("Twilio API secret (shown once): ").strip(),
    }
    plant(args.target, values)
    print("ACORN_PLANTED: all three names are PRESENT; values were not displayed.")


if __name__ == "__main__":
    main()
