#!/usr/bin/env python3
"""Mint a Monarch Money session token — run this LOCALLY, once.

The scheduled GitHub Action logs in with a saved token instead of email/password,
because Monarch rate-limits (HTTP 429) the login endpoint from cloud IPs. This
script performs the one real login from your own machine and prints the resulting
session token. Copy that token into the GitHub Actions secret `MONARCH_TOKEN`.

Nothing is read from the command line or environment — you're prompted, and the
password / MFA seed use hidden input so they never hit your shell history.

Usage:
    cd calendar && source .venv/bin/activate
    python scripts/mint_token.py
"""

import asyncio
import getpass
import sys

from monarchmoney import MonarchMoney


def normalize_seed(raw: str) -> str:
    """Monarch shows the setup key in spaced groups; base32 needs it clean.

    Strip whitespace, uppercase, and pad to a multiple of 8 with '=' so the
    TOTP library can base32-decode it without an 'Incorrect padding' error.
    """
    s = "".join(raw.split()).upper()
    if len(s) % 8:
        s += "=" * (8 - len(s) % 8)
    return s


async def main() -> int:
    email = input("Monarch email: ").strip()
    password = getpass.getpass("Monarch password (hidden): ")
    mfa_raw = getpass.getpass("MFA setup key / base32 seed (hidden, blank if 2FA off): ").strip()
    mfa = normalize_seed(mfa_raw) if mfa_raw else None

    mm = MonarchMoney()
    try:
        # Don't touch any saved session; do a real login this one time.
        await mm.login(
            email,
            password,
            use_saved_session=False,
            save_session=False,
            mfa_secret_key=mfa,
        )
    except Exception as e:  # noqa: BLE001 - surface any auth failure plainly
        print(f"\nLogin failed: {e}", file=sys.stderr)
        return 1

    token = mm.token
    if not token:
        print("\nLogin succeeded but no token was returned.", file=sys.stderr)
        return 1

    print("\n" + "=" * 60)
    print("SESSION TOKEN — copy this into the GitHub secret MONARCH_TOKEN:")
    print("=" * 60)
    print(token)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
