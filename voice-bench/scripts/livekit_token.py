"""Mint a LiveKit client token for one of Chris's surfaces (phone, browser).

Run:  python scripts/livekit_token.py [identity]     (default identity: chris)
Uses the same env/defaults as src/bot_livekit.py; prints the token and a
ready-to-use LiveKit Meet URL for a quick browser/phone test against the
self-hosted server (media flows only between the client and Gammy).
"""

import os
import sys

from livekit import api

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "vp2-local-dev-secret-change-me-32B")
LIVEKIT_ROOM = os.getenv("LIVEKIT_ROOM", "voice-bench")


def main():
    identity = sys.argv[1] if len(sys.argv) > 1 else "chris"
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=LIVEKIT_ROOM))
        .to_jwt()
    )
    print(f"room:     {LIVEKIT_ROOM}")
    print(f"server:   {LIVEKIT_URL}   (from another device use ws://<gammy-lan-ip>:7880)")
    print(f"identity: {identity}")
    print(f"token:\n{token}")
    print(
        "\nQuick test from a phone browser on the same Wi-Fi:\n"
        f"  https://meet.livekit.io/custom?liveKitUrl=ws://<gammy-lan-ip>:7880&token={token}\n"
        "(The Meet page is just a client UI; audio stays between the phone and Gammy.)"
    )


if __name__ == "__main__":
    main()
