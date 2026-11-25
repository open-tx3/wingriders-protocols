# WingRiders V2 — swap request

[WingRiders](https://www.wingriders.com/) is an automated market maker on Cardano.
A V2 swap takes two transactions: the user locks a **request** at the V2 request
validator, then a WingRiders agent applies it against the pool and pays the
result to the user ([how a swap works](https://docs.wingriders.com/actions/swapping)).

This interface covers the first transaction only, on one pinned pool:
`place_swap_request` offers ADA to the **ADA/SNEK** pool on **mainnet** and asks
for at least a minimum amount of SNEK in return. Fulfilment is the agent's
transaction, and reclaim, liquidity and other pools are out of scope.

Source: [`WingRiders/dex-v2-contracts@280a9e8`](https://github.com/WingRiders/dex-v2-contracts/tree/280a9e895077ab746c2713880efba79038fea50f)
([request datum](https://github.com/WingRiders/dex-v2-contracts/blob/280a9e895077ab746c2713880efba79038fea50f/src/DEX/Types/Request.hs),
[checks the pool applies](https://github.com/WingRiders/dex-v2-contracts/blob/280a9e895077ab746c2713880efba79038fea50f/src/DEX/Pool.hs#L563-L668)).
Tagged release source: [`v0.1.0`](https://github.com/open-tx3/wingriders-protocols/tree/v0.1.0/wingriders-v2)
(the tag is created when the version is published).

## Operation

| Transaction | Network | What it does |
|---|---|---|
| `place_swap_request` | mainnet | Locks `offer_lovelace + oil + agent_fee` at the request validator with a `Swap SwapAToB` request datum. Runs no script. |

The owner pays from one or more of their UTxOs and must sign with the key
`owner_pkh`, which the transaction lists as a required signer. The request
names the owner as both beneficiary (receives the swap result) and owner (only
key that may reclaim), so a wrong hash would lock the request or send its
proceeds elsewhere.

## Deployment (`mainnet` profile)

| Item | Value |
|---|---|
| Request validator (PlutusV2) | `c134d839a64a5dfb9b155869ef3f34280751a622f69958baa8ffd29c` |
| `RequestScript` party | `addr1w8qnfkpe5e99m7umz4vxnmelxs5qw5dxytmfjk964rla98q605wte` |
| Pool | ADA/SNEK, pool validator `af97793b8702f381976cec83e303e9ce17781458c73c4bb16fe02b83` |
| `pool_asset_b_policy` | `279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f` (SNEK) |
| `pool_asset_b_name` | `534e454b` (`SNEK`) |
| `agent_fee` | `2000000` lovelace, the pool datum's `agentFeeAda` |
| `oil` | `2000000` lovelace, the contract minimum `requestOilAda`; refunded with the result |

Every coordinate and where it was read is in
[`fixtures/deployment.json`](fixtures/deployment.json).

## Inputs

| Name | Type | Unit | Meaning |
|---|---|---|---|
| `owner` | party | bech32 address | Wallet that pays and receives change. Must be a key/key base address. |
| `owner_pkh` | Bytes | 28-byte hex | Payment key hash of `owner`. |
| `owner_stake_key` | Bytes | 28-byte hex | Stake key hash of `owner`. |
| `offer_lovelace` | Int | lovelace | ADA offered to the pool, excluding oil and agent fee. |
| `min_receive` | Int | whole SNEK (the token has no decimals) | Minimum SNEK the agent must pay out. |
| `deadline_ms` | Int | POSIX **milliseconds** | Last moment the agent may apply the request. |

`owner_pkh` and `owner_stake_key` must be the two halves of `owner`;
`min_receive` comes from a current pool quote; `deadline_ms` must be in the
future when the request lands.

- [`invoke-args/place_swap_request.json`](invoke-args/place_swap_request.json)
  is the live-resolution example: a template whose values you fill for your
  own wallet before each run (see [Use it](#use-it)).
- [`fixtures/reference-args.json`](fixtures/reference-args.json) holds the
  historical inputs of the recorded request below. They are reproducible
  evidence, not a runnable example: their deadline and owner are that
  request's.

## Expected effects

One output at `RequestScript` holding only ADA,
`offer_lovelace + oil + agent_fee` lovelace, with this inline datum:

| Field | Value |
|---|---|
| `oil` | `oil` |
| `beneficiary`, `owner` | `owner_pkh` + `owner_stake_key` |
| `compensation_datum`, `compensation_datum_type` | `[]`, `NoDatum` |
| `deadline` | `deadline_ms` |
| asset A / asset B | ADA (`""`, `""`) / `pool_asset_b_policy`.`pool_asset_b_name` |
| `action` | `Swap { SwapAToB, min_receive }` |
| `a_scale`, `b_scale` | `1`, `1` |

The agent later returns at least `min_receive` SNEK plus the `oil` to the
owner and keeps `agent_fee`.

Reference request: mainnet transaction
[`a94abb49…f103e`](https://cexplorer.io/tx/a94abb492b23ec07d16d38f0964e3f664851ca19fb4b9b403b9e5b6b544f103e)
(256 000 000 lovelace = 252 000 000 offered + 2 000 000 oil + 2 000 000 agent
fee; minimum 89 185 SNEK; deadline 1795499508453), applied in
[`dd985e27…a33fc`](https://cexplorer.io/tx/dd985e27a493ad0586a786f40b9ad4f1c6d66ade4f28491b08a88b5d493a33fc).
The [comparison report](invoke-args/comparison-report.md) decodes it next to the
transaction this interface builds.

## Use it

```bash
trix use open-tx3/wingriders-v2:0.1.0
```

| Language | Package | Generate the client |
|---|---|---|
| TypeScript | [`tx3-sdk`](https://www.npmjs.com/package/tx3-sdk) (npm) | `trix codegen --plugin ts-client` |
| Rust | [`tx3-sdk`](https://crates.io/crates/tx3-sdk) (crates.io) | `trix codegen --plugin rust-client` |
| Python | [`tx3-sdk`](https://pypi.org/project/tx3-sdk/) (PyPI) | `trix codegen --plugin python-client` |
| Go | [`github.com/tx3-lang/go-sdk/sdk`](https://pkg.go.dev/github.com/tx3-lang/go-sdk/sdk) | `trix codegen --plugin go-client` |
| Java | [`land.tx3:tx3-sdk`](https://central.sonatype.com/artifact/land.tx3/tx3-sdk) (Maven Central) | `trix codegen --plugin java-client` |
| Swift | [`Tx3SDK`](https://github.com/tx3-lang/swift-sdk) (Swift Package Manager) | `trix codegen --plugin swift-client` |

To build an unsigned transaction for your own wallet, refresh the live inputs
from this directory, then invoke. Take `--min-receive` from a current quote
(the WingRiders app, or the pool reserves less your slippage).
[`scripts/live_args.py`](../scripts/live_args.py) splits your address into
the two hashes and sets the deadline from the current clock (180 minutes by
default):

```bash
python3 ../scripts/live_args.py --owner addr1q... --offer-lovelace 100000000 \
  --min-receive 35000 > invoke-args/place_swap_request.json
trix invoke --profile mainnet --skip-submit --args-json-path invoke-args/place_swap_request.json
```

The protocol guide, Fluent tools and Skill for this version are linked here
when they are published.

## Checks

`trix check` and `trix build`, then
[`scripts/check-request.py`](../scripts/check-request.py). It:

- decodes the recorded and the generated request and asserts the effects above;
- requires the [negative fixtures](fixtures/negative/) (deadline in seconds,
  lost deposit, reversed direction) to be rejected;
- checks that the `RequestScript` address is the request validator and that
  the historical `owner` carries `owner_pkh` and `owner_stake_key`;
- evaluates the freshly built `place_swap_request` TIR for the historical
  inputs and requires the generated transaction's request output (address,
  lovelace, datum) and required signers to equal it;
- pins the rest of that TIR to its current shape: one payment input declared
  `input*` (so it may draw several UTxOs), from `Owner`, covering the request
  and fees; one change output back to `Owner`; no other output, and no
  validity interval, mint, burn, reference, collateral or metadata. Any other
  construct fails and is named, so a deliberate addition extends the check;
- requires the generated transaction to hold only the request and change
  outputs, its change paid to the fixture's `resolved_from`, and no body
  fields beyond inputs, outputs, fee, required signers and network id, nor
  metadata;
- requires each fixture's `tx_hash` to hash its transaction body, and the
  generated fixture's `tir_sha256` to match the built TIR.

Which wallet UTxOs the payment selects, and the fee, are not compared: they
depend on the payer's wallet at resolution time. A change to `main.tx3` that
alters any checked part of the built transaction, or a toolchain release that
changes the TIR encoding, fails these checks until the generated fixture is
rebuilt. A toolchain release that also re-shapes a TIR node the shape check
pins keeps failing after the rebuild until the check in
`scripts/check-request.py` is updated to the new encoding. From this
directory:

```bash
python3 ../scripts/regenerate.py --resolve-from addr1...
python3 ../scripts/check-request.py
```

`regenerate.py` invokes the historical inputs unsigned and never submits.
`--resolve-from` names any funded mainnet address to pay from (about 260 ADA),
so the refresh does not depend on the reference wallet; the datum and signer
keep the reference hashes. Without it the reference owner pays.

## License

Apache-2.0, see [LICENSE](../LICENSE). The WingRiders contracts this interface
describes are GPL-3.0 and are not copied here.
