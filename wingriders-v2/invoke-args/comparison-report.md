# WingRiders V2 `place_swap_request` — comparison report

Compares the unsigned transaction built by this interface with a publicly
recorded V2 swap request on the same pool. `scripts/check-request.py` repeats
every row marked *checked* on each CI run, from the fixtures in
[`../fixtures`](../fixtures).

## Transactions

| Role | Tx hash | Source |
|---|---|---|
| Reference request (ADA → SNEK) | `a94abb492b23ec07d16d38f0964e3f664851ca19fb4b9b403b9e5b6b544f103e` | mainnet, block 14240034, slot 203911631 ([fixture](../fixtures/reference-request.json)) |
| Agent applying it | `dd985e27a493ad0586a786f40b9ad4f1c6d66ade4f28491b08a88b5d493a33fc` | mainnet, same pool |
| Generated (unsigned) | `783ece2f60ef89e5017e60632e2538612eade6afb01ec5cdcc6ff2e8531b31d7` | `scripts/regenerate.py` (`trix invoke --profile mainnet --skip-submit` with `fixtures/reference-args.json`), trix 0.28.0 ([fixture](../fixtures/generated-request.json)) |

The historical args in [`fixtures/reference-args.json`](../fixtures/reference-args.json)
replay the reference owner, amounts and deadline, so the two requests should
decode to the same effects. They are not the live example: that is the
template in [`place_swap_request.json`](place_swap_request.json), refreshed per
run as the README describes.

## Request output

| Effect | Reference | Generated | |
|---|---|---|---|
| Validator (payment credential) | `c134d839…ffd29c` | `c134d839…ffd29c` | checked |
| Lovelace | 256 000 000 | 256 000 000 | checked |
| Other assets | none | none | checked |
| Offered = lovelace − oil − agent fee | 252 000 000 | 252 000 000 | checked |
| `oil` (deposit, ≥ 2 000 000) | 2 000 000 | 2 000 000 | checked |
| `beneficiary` | key `71692fca…e61dba`, stake `513afdfa…71d9df` | same | checked |
| `owner` | same as beneficiary | same | checked |
| Compensation datum / type | `[]` / `No` | `[]` / `No` | checked |
| `deadline` (POSIX ms) | 1795499508453 (6 h after the block) | 1795499508453 | checked |
| Asset A | ADA | ADA | checked |
| Asset B | `279c909f…927a3f`.`SNEK` | same | checked |
| `action` | `Swap SwapAToB 89185` | `Swap SwapAToB 89185` | checked |
| `aScale`, `bScale` | 1, 1 | 1, 1 | checked |

The pool datum read in the applying transaction carries `agentFeeAda =
2000000`. The agent returned 89 436 SNEK (above the 89 185 minimum) and
2 500 000 lovelace (at least the oil) to the beneficiary.

Both requests go to the plain validator address `addr1w8qnfkpe…605wte`, with
no staking part.

## Negative fixtures

Each is the reference request output with one effect broken; the check must
reject it for the named reason.

| Fixture | Change | Rejected as |
|---|---|---|
| [`deadline-in-seconds`](../fixtures/negative/deadline-in-seconds.json) | deadline 1795499508 (seconds) | `deadline-units` |
| [`lost-deposit`](../fixtures/negative/lost-deposit.json) | value lacks the 2 ADA oil | `deposit-arithmetic` |
| [`reversed-direction`](../fixtures/negative/reversed-direction.json) | `SwapBToA` on an ADA offer | `direction` |

## Expected differences

| Difference | Reason |
|---|---|
| Datum encoding | The reference uses indefinite-length CBOR arrays, Tx3 definite-length. The Plutus data is identical; the datum bytes and hash differ. |
| Wallet inputs, change, fee | Different UTxOs at resolution time. `--skip-submit` builds with a provisional fee. |
| TTL | The reference sets slot 203911797; this interface sets no validity interval. The deadline in the datum bounds fulfilment. |
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
and requires the generated request output and signers to equal it. It also
pins the rest of the TIR (one `input*` payment from `Owner`, one change back
to `Owner`, nothing else) and requires the generated transaction to hold only
those two outputs, with the change paid to `resolved_from`. A change to
`main.tx3` in any of those parts cannot pass against a stale fixture; the
selected wallet UTxOs and the fee are not compared.
