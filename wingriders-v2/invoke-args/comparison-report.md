# WingRiders V2 `place_swap_request` — comparison report

Compares the unsigned transaction built by this interface with a publicly
recorded V2 swap request on the same pool. `scripts/check-request.py` repeats
every row marked *checked* on each CI run, from the fixtures in
[`../fixtures`](../fixtures).

## Transactions

| Role | Tx hash | Source |
|---|---|---|
| Reference request (ADA → DJED) | `92c25e5ec64e8c2843d282d4b1c9469e815bf29823b16377fd5040ff06220e02` | mainnet, block 14243637, slot 203983905 ([fixture](../fixtures/reference-request.json)) |
| Agent applying it | `57b5303f71e40df66cda31a59cfc105ff8c4f3dd6a2f87e24e5ec1b663c336a9` | mainnet, same pool |
| Generated (unsigned) | `1c8c9a17e1a12f7b510202e644d3d9dba29fb53777738ac4a517839704d49892` | `scripts/regenerate.py` (`trix invoke --profile mainnet --skip-submit` with `fixtures/reference-args.json`), trix 0.28.0 ([fixture](../fixtures/generated-request.json)) |

The historical args in [`fixtures/reference-args.json`](../fixtures/reference-args.json)
replay the reference owner, amounts and deadline, so the two requests should
decode to the same effects. They are not the live example: that is the
template in [`place_swap_request.json`](place_swap_request.json), refreshed per
run as the README describes.

## Request output

| Effect | Reference | Generated | |
|---|---|---|---|
| Validator (payment credential) | `c134d839…ffd29c` | `c134d839…ffd29c` | checked |
| Lovelace | 440 040 900 | 440 040 900 | checked |
| Other assets | none | none | checked |
| Offered = lovelace − oil − agent fee | 436 040 900 | 436 040 900 | checked |
| `oil` (deposit, ≥ 2 000 000) | 2 000 000 | 2 000 000 | checked |
| `beneficiary` | key `4263f524…688446`, stake `c0bd755d…cf387d` | same | checked |
| `owner` | same as beneficiary | same | checked |
| Compensation datum / type | `[]` / `No` | `[]` / `No` | checked |
| `deadline` (POSIX ms) | 1795560969000 (3 h after the block) | 1795560969000 | checked |
| Asset A | ADA | ADA | checked |
| Asset B | `8db269c3…a1cd61`.`DjedMicroUSD` | same | checked |
| `action` | `Swap SwapAToB 62220622` | `Swap SwapAToB 62220622` | checked |
| `aScale`, `bScale` | 1, 1 | 1, 1 | checked |

The pool datum read in the applying transaction carries `agentFeeAda =
2000000`. The agent returned 62 297 995 DJED (above the 62 220 622 minimum) and
2 500 000 lovelace (at least the oil) to the beneficiary.

## Negative fixtures

Each is the reference request output with one effect broken; the check must
reject it for the named reason.

| Fixture | Change | Rejected as |
|---|---|---|
| [`deadline-in-seconds`](../fixtures/negative/deadline-in-seconds.json) | deadline 1795560969 (seconds) | `deadline-units` |
| [`lost-deposit`](../fixtures/negative/lost-deposit.json) | value lacks the 2 ADA oil | `deposit-arithmetic` |
| [`reversed-direction`](../fixtures/negative/reversed-direction.json) | `SwapBToA` on an ADA offer | `direction` |

## Expected differences

| Difference | Reason |
|---|---|
| Request address staking part | The reference wallet put its own stake key on the request address (`addr1z8…`); the profile binds the plain validator address (`addr1w8…`). The pool checks only the validator hash. Pass `requestscript` in the args to use a staked variant. |
| Datum encoding | The reference uses indefinite-length CBOR arrays, Tx3 definite-length. The Plutus data is identical; the datum bytes and hash differ. |
| Wallet inputs, change, fee | Different UTxOs at resolution time. `--skip-submit` builds with a provisional fee. |
| TTL | The reference sets slot 203987478; this interface sets no validity interval. The deadline in the datum bounds fulfilment. |
| Required signers | The generated transaction lists `owner_pkh` (body field 14) so only the owner's key can authorize the request; the reference lists none, its wallet signs as the spender. |
| Witnesses | The generated transaction is unsigned. |

## Reproduce

```bash
cd wingriders-v2
trix build
python3 ../scripts/regenerate.py --resolve-from addr1...
python3 ../scripts/check-request.py
```

`regenerate.py` replays the historical inputs, paying from any funded mainnet
address (the reference owner by default), so its inputs, change and hash
differ from the checked-in generated fixture; the request output and signer
do not. The check evaluates the freshly built TIR for the historical inputs
and requires the generated request output and signers to equal it, so a
change to `main.tx3` cannot pass against a stale fixture.
