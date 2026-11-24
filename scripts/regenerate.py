#!/usr/bin/env python3
"""Rebuild fixtures/generated-request.json from the current main.tx3.

Invokes `place_swap_request` (unsigned, never submitted) with the historical
inputs of fixtures/reference-args.json, but pays from `--resolve-from`, any
funded mainnet address, so the refresh never depends on the reference wallet.
The datum and signer keep the reference hashes. Needs trix and network access.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_request", HERE / "check-request.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

GENERATED = check.FIXTURES / "generated-request.json"


def trix_bin():
    """trix from TX3_TRIX_PATH, PATH, or tx3up's default install."""
    found = os.environ.get("TX3_TRIX_PATH") or shutil.which("trix")
    return found or str(Path.home() / ".tx3/default/bin/trix")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--resolve-from", metavar="ADDR",
                    help="funded mainnet address that pays (default: the reference owner)")
    opts = ap.parse_args()
    args = json.loads((check.FIXTURES / "reference-args.json").read_text())
    if opts.resolve_from:
        if check.bech32_bytes(opts.resolve_from)[0] & 0x0F != 1:
            ap.error(f"{opts.resolve_from} is not a mainnet address")
        args["owner"] = opts.resolve_from
    trix = trix_bin()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "args.json"
        path.write_text(json.dumps(args))
        out = subprocess.run([trix, "invoke", "--profile", "mainnet", "--skip-submit",
                              "--args-json-path", str(path)],
                             cwd=check.PROTOCOL, stdin=subprocess.DEVNULL,
                             capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"trix invoke failed:\n{out.stdout}{out.stderr}")
    built = json.loads(out.stdout[out.stdout.index("{"):])
    version = subprocess.run([trix, "--version"], capture_output=True, text=True).stdout.strip()

    fixture = json.loads(GENERATED.read_text())
    fixture.update({
        "tx_hash": built["hash"],
        "toolchain": version,
        "resolved_from": args["owner"],
        "tir_sha256": check.tir_digest(json.loads(check.tii_path().read_text())),
    })
    fixture.pop("tx_cbor", None)
    fixture["tx_cbor"] = built["cbor"]  # keep the long field last
    GENERATED.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"wrote {GENERATED.relative_to(check.ROOT)}: {built['hash']} ({version}); "
          "run scripts/check-request.py to verify it")


if __name__ == "__main__":
    main()
