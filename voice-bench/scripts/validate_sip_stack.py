"""Validate the VP-2 SIP scaffold without starting containers or printing secrets."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "livekit" / "docker-compose.sip.yml"
SECRET_FILE = Path(
    os.environ.get(
        "VP2_LIVEKIT_ENV_FILE",
        Path.home() / ".novacore" / "secrets" / "vp2-livekit.env",
    )
)
EXPECTED_SERVICES = {"redis", "livekit", "sip"}
PINNED_IMAGES = {
    "redis:7.4-alpine@sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf",
    "livekit/sip:v1.11.0@sha256:eac7a15dbf8173b04ce1a59ed95f4b07da9db4ff796ab1fb86e92a499d3ee8d8",
}


def run(*args: str, capture: bool = False) -> str:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip() if capture else ""


def main() -> None:
    if not SECRET_FILE.is_file():
        raise SystemExit(f"missing external env file: {SECRET_FILE}")

    compose_cmd = (
        "docker",
        "compose",
        "-f",
        str(COMPOSE),
        "--env-file",
        str(SECRET_FILE),
    )
    run(*compose_cmd, "config", "--quiet")
    services = set(run(*compose_cmd, "config", "--services", capture=True).splitlines())
    if services != EXPECTED_SERVICES:
        raise SystemExit(f"unexpected services: {sorted(services)}")

    compose_text = COMPOSE.read_text(encoding="utf-8")
    for image in PINNED_IMAGES:
        if image not in compose_text:
            raise SystemExit(f"missing pinned image: {image.split('@', 1)[0]}")
        run("docker", "manifest", "inspect", image)

    before = run("docker", "ps", "--format", "{{.Names}}|{{.Image}}", capture=True)
    after = run("docker", "ps", "--format", "{{.Names}}|{{.Image}}", capture=True)
    if before != after:
        raise SystemExit("running container set changed during no-start validation")
    if "livekit-livekit-1|livekit/livekit-server:v1.9" not in after:
        raise SystemExit("resident Gate-1 LiveKit container is not present")

    print("SIP_SCAFFOLD_VALIDATION_PASS services=livekit,redis,sip activated=false")


if __name__ == "__main__":
    main()
