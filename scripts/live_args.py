#!/usr/bin/env python3
"""Write live invoke args for `place_swap_request` from an owner address.

Splits a key/key mainnet base address into `owner_pkh` and `owner_stake_key`
and sets `deadline_ms` from the current clock. `min_receive` must come from a
current pool quote. Prints the JSON; standard library only.
"""
import argparse
import json
import time

BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_bytes(addr):
    """Decode a bech32 address into its raw bytes (checksum not verified)."""
    data = [BECH32.index(c) for c in addr.rsplit("1", 1)[1]][:-6]
    acc, bits, out = 0, 0, bytearray()
    for v in data:
        acc, bits = (acc << 5) | v, bits + 5
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return bytes(out)


def owner_hashes(addr):
    """Return (payment key hash, stake key hash) of a key/key mainnet base address."""
    raw = bech32_bytes(addr)
    if raw[0] != 0x01 or len(raw) != 57:
        raise ValueError(f"{addr} is not a key/key mainnet base address")
    return raw[1:29].hex(), raw[29:57].hex()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--owner", required=True, help="owner key/key base address (addr1q…)")
    ap.add_argument("--offer-lovelace", type=int, required=True, help="ADA offered, in lovelace")
    ap.add_argument("--min-receive", type=int, required=True, help="minimum SNEK (whole tokens; SNEK has no decimals)")
    ap.add_argument("--deadline-minutes", type=int, default=180, help="deadline from now (default 180)")
    args = ap.parse_args()
    if not 0 < args.deadline_minutes <= 30 * 24 * 60:
        ap.error("--deadline-minutes must be between 1 and 43200 (30 days)")
    pkh, stake = owner_hashes(args.owner)
    print(json.dumps({
        "owner": args.owner,
        "owner_pkh": pkh,
        "owner_stake_key": stake,
        "offer_lovelace": args.offer_lovelace,
        "min_receive": args.min_receive,
        "deadline_ms": (int(time.time()) + args.deadline_minutes * 60) * 1000,
    }, indent=2))


if __name__ == "__main__":
    main()
