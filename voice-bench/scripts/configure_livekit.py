"""Create external LiveKit credentials without printing secrets."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(
    os.getenv(
        "VP2_LIVEKIT_ENV_FILE",
        str(Path.home() / ".novacore" / "secrets" / "vp2-livekit.env"),
    )
)


def tailscale_identity() -> tuple[str, str]:
    raw = subprocess.check_output(["tailscale", "status", "--json"], text=True)
    status = json.loads(raw)
    self_node = status["Self"]
    ip = self_node["TailscaleIPs"][0]
    dns = self_node["DNSName"].rstrip(".")
    return ip, dns


def main() -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                name, value = line.split("=", 1)
                existing[name] = value

    node_ip, dns_name = tailscale_identity()
    values = {
        "LIVEKIT_API_KEY": existing.get("LIVEKIT_API_KEY", "vp2_" + secrets.token_hex(8)),
        "LIVEKIT_API_SECRET": existing.get(
            "LIVEKIT_API_SECRET", secrets.token_urlsafe(48)
        ),
        "LIVEKIT_NODE_IP": node_ip,
        "LIVEKIT_PUBLIC_URL": f"wss://{dns_name}:7880",
    }
    ENV_FILE.write_text(
        "".join(f"{name}={value}\n" for name, value in values.items()),
        encoding="utf-8",
    )
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass
    print(
        f"CONFIGURED {ENV_FILE} (credentials redacted; "
        f"node_ip={node_ip}; public_url={values['LIVEKIT_PUBLIC_URL']})"
    )


if __name__ == "__main__":
    main()
