#!/usr/bin/env python3
"""Semantic check of WingRiders V2 swap requests against recorded fixtures.

Decodes the request output of each fixture transaction (or bare output),
asserts the expected effects from the deployment profile, requires every
negative fixture to fail with its named reason, and checks that the exported
TII, invoke args and README use the same names. Standard library only.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "wingriders-v2"
FIXTURES = PROTOCOL / "fixtures"
TII = PROTOCOL / ".tx3/tii/open-tx3/wingriders-v2/0.1.0/main.tii"

# Deadlines are POSIX milliseconds; a seconds value is ~1000x too small.
MAX_DEADLINE_WINDOW_MS = 30 * 24 * 3600 * 1000


class Tag:
    def __init__(self, tag, value):
        self.tag, self.value = tag, value


class Constr:
    def __init__(self, index, fields):
        self.index, self.fields = index, fields


def cbor_decode(data, pos=0):
    """Decode one CBOR item; returns (value, next_pos)."""
    head = data[pos]
    major, info = head >> 5, head & 0x1F
    pos += 1
    if info < 24:
        arg = info
    elif info in (24, 25, 26, 27):
        size = 1 << (info - 24)
        arg = int.from_bytes(data[pos:pos + size], "big")
        pos += size
    elif info == 31:
        arg = None
    else:
        raise ValueError(f"unsupported CBOR header {head:#x}")
    if major == 0:
        return arg, pos
    if major == 1:
        return -1 - arg, pos
    if major in (2, 3):
        if arg is None:
            chunks = []
            while data[pos] != 0xFF:
                chunk, pos = cbor_decode(data, pos)
                chunks.append(chunk)
            joined = b"".join(chunks) if major == 2 else "".join(chunks)
            return joined, pos + 1
        raw = data[pos:pos + arg]
        return (raw if major == 2 else raw.decode()), pos + arg
    if major in (4, 5):
        items = []
        count = 0
        while (arg is None and data[pos] != 0xFF) or (arg is not None and count < arg * (major - 3)):
            item, pos = cbor_decode(data, pos)
            items.append(item)
            count += 1
        if arg is None:
            pos += 1
        if major == 4:
            return items, pos
        return dict(zip(items[0::2], items[1::2])), pos
    if major == 6:
        value, pos = cbor_decode(data, pos)
        return Tag(arg, value), pos
    if major == 7 and info in (20, 21, 22):
        return {20: False, 21: True, 22: None}[info], pos
    raise ValueError(f"unsupported CBOR major type {major}")


def plutus(value):
    """Normalize decoded CBOR into Plutus data (Constr / int / bytes / list)."""
    if isinstance(value, Tag):
        if 121 <= value.tag <= 127:
            return Constr(value.tag - 121, [plutus(f) for f in value.value])
        if 1280 <= value.tag <= 1400:
            return Constr(value.tag - 1280 + 7, [plutus(f) for f in value.value])
        if value.tag == 102:
            return Constr(value.value[0], [plutus(f) for f in value.value[1]])
        raise ValueError(f"unexpected tag {value.tag} in datum")
    if isinstance(value, list):
        return [plutus(v) for v in value]
    return value


def tx_outputs(tx_cbor_hex):
    tx, _ = cbor_decode(bytes.fromhex(tx_cbor_hex))
    outputs = []
    for out in tx[0][1]:
        if isinstance(out, dict):
            address, value, datum_option = out[0], out[1], out.get(2)
        else:
            address, value = out[0], out[1]
            datum_option = [0, out[2]] if len(out) > 2 else None
        datum = None
        if datum_option is not None:
            if datum_option[0] != 1:
                raise ValueError("request datum must be inline")
            datum = datum_option[1].value.hex()
        coin, assets = (value, {}) if isinstance(value, int) else (value[0], value[1])
        outputs.append({"address": address.hex(), "lovelace": coin,
                        "assets": {p.hex(): {n.hex(): q for n, q in m.items()} for p, m in assets.items()},
                        "datum": datum})
    return outputs


def key_address(addr):
    """Decode a Plutus key/key address into (payment pkh, stake key hash)."""
    payment, staking = addr.fields
    if payment.index != 0:
        raise ValueError("address payment credential is not a key")
    if staking.index != 0:
        return payment.fields[0].hex(), None
    stake_cred = staking.fields[0]
    if stake_cred.index != 0 or stake_cred.fields[0].index != 0:
        raise ValueError("address staking credential is not a key hash")
    return payment.fields[0].hex(), stake_cred.fields[0].fields[0].hex()


def decode_request(output):
    d = plutus(cbor_decode(bytes.fromhex(output["datum"]))[0])
    if not isinstance(d, Constr) or d.index != 0 or len(d.fields) != 13:
        raise ValueError("datum is not a 13-field RequestDatum")
    (oil, beneficiary, owner, comp_datum, comp_type, deadline,
     a_sym, a_tok, b_sym, b_tok, action, a_scale, b_scale) = d.fields
    if action.index != 0:
        raise ValueError(f"action constructor {action.index} is not Swap")
    direction, min_wanted = action.fields
    return {
        "validator": output["address"][2:58],
        "lovelace": output["lovelace"],
        "assets": output["assets"],
        "oil": oil,
        "beneficiary": key_address(beneficiary),
        "owner": key_address(owner),
        "compensation_datum_type": comp_type.index,
        "compensation_datum": comp_datum,
        "deadline": deadline,
        "asset_a": (a_sym.hex(), a_tok.hex()),
        "asset_b": (b_sym.hex(), b_tok.hex()),
        "direction": "SwapAToB" if direction.index == 0 else "SwapBToA",
        "min_wanted": min_wanted,
        "scales": (a_scale, b_scale),
    }


def find_request(outputs, script_hash):
    for out in outputs:
        header = int(out["address"][:2], 16)
        if header >> 4 in (1, 3, 5, 7) and out["address"][2:58] == script_hash:
            return out
    raise ValueError("no output at the request validator")


def check_effects(req, deployment, expected):
    """Raise ValueError naming the first effect that breaks the expectation."""
    def need(cond, reason):
        if not cond:
            raise ValueError(reason)
    pool = deployment["pool"]
    need(req["validator"] == deployment["request_script_hash"], "validator")
    need(req["direction"] == "SwapAToB", "direction")
    need(req["asset_a"] == ("", ""), "asset-a")
    need(req["asset_b"] == (pool["asset_b_policy"], pool["asset_b_name"]), "asset-b")
    need(req["oil"] >= deployment["min_oil"], "oil-minimum")
    need(not req["assets"], "unexpected-assets")
    offered = req["lovelace"] - req["oil"] - pool["agent_fee"]
    need(offered == expected["offer_lovelace"], "deposit-arithmetic")
    need(req["min_wanted"] == expected["min_receive"], "min-receive")
    owner = (expected["owner_pkh"], expected["owner_stake_key"])
    need(req["beneficiary"] == owner, "beneficiary")
    need(req["owner"] == owner, "owner")
    need(req["compensation_datum_type"] == 0 and req["compensation_datum"] == [], "compensation-datum")
    need(req["scales"] == (1, 1), "scales")
    created_ms = expected["created_posix_s"] * 1000
    need(created_ms < req["deadline"] <= created_ms + MAX_DEADLINE_WINDOW_MS, "deadline-units")
    need(req["deadline"] == expected["deadline_ms"], "deadline")


def check_interface(deployment):
    tii = json.loads(TII.read_text())
    tx = tii["transactions"]["place_swap_request"]
    params = set(tx["params"]["properties"])
    profile = tii["profiles"]["mainnet"]
    pool = deployment["pool"]
    env = {"pool_asset_b_policy": pool["asset_b_policy"], "pool_asset_b_name": pool["asset_b_name"],
           "agent_fee": pool["agent_fee"], "oil": deployment["min_oil"]}
    assert profile["environment"] == env, f"mainnet profile env {profile['environment']} != {env}"
    assert profile["parties"]["requestscript"] == deployment["request_address"], "mainnet RequestScript"
    args = json.loads((PROTOCOL / "invoke-args/place_swap_request.json").read_text())
    names = params | set(tii["parties"])
    assert set(args) <= names, f"invoke args not in interface: {set(args) - names}"
    assert set(tx["params"]["required"]) <= set(args), "invoke args miss a required param"
    readme = (PROTOCOL / "README.md").read_text()
    missing = [n for n in params | set(env) if f"`{n}`" not in readme]
    assert not missing, f"README does not document {missing}"


def main():
    deployment = json.loads((FIXTURES / "deployment.json").read_text())
    check_interface(deployment)
    print("ok   interface: TII, mainnet profile, invoke args and README agree")
    decoded = {}
    for name in ("reference", "generated"):
        fx = json.loads((FIXTURES / f"{name}-request.json").read_text())
        req = decode_request(find_request(tx_outputs(fx["tx_cbor"]), deployment["request_script_hash"]))
        check_effects(req, deployment, fx["expected"])
        decoded[name] = req
        print(f"ok   {name}: {fx['tx_hash']} matches its expected effects")
    diff = [k for k in decoded["reference"] if decoded["reference"][k] != decoded["generated"][k]]
    assert not diff, f"generated request differs from the reference in {diff}"
    print("ok   generated request decodes to the same effects as the reference")
    failures = 0
    for path in sorted((FIXTURES / "negative").glob("*.json")):
        fx = json.loads(path.read_text())
        try:
            check_effects(decode_request(fx["output"]), deployment, fx["expected"])
            reason = None
        except ValueError as err:
            reason = str(err)
        if reason == fx["rejects"]:
            print(f"ok   negative/{path.name}: rejected ({reason})")
        else:
            failures += 1
            print(f"FAIL negative/{path.name}: expected rejection '{fx['rejects']}', got {reason!r}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
