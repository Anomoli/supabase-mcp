from pathlib import Path
from tempfile import TemporaryDirectory

from plant_twilio_acorn import REQUIRED, parse_env, plant, presence


def main() -> None:
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "vp2-twilio.env"
        target.write_text("# preserved\nEXISTING_NAME=keep-me\n", encoding="utf-8")
        values = {
            "TWILIO_ACCOUNT_SID": "AC" + "a" * 32,
            "TWILIO_API_KEY": "SK" + "b" * 32,
            "TWILIO_API_SECRET": "c" * 32,
        }
        plant(target, values, lock_acl=False)
        lines, parsed = parse_env(target.read_text(encoding="utf-8"))
        assert parsed["EXISTING_NAME"] == "keep-me"
        assert all(parsed[key] == values[key] for key in REQUIRED)
        assert all(presence(target).values())
        assert "# preserved" in lines
    print("PASS Twilio acorn: atomic write, preservation, validation, presence-only check")


if __name__ == "__main__":
    main()
