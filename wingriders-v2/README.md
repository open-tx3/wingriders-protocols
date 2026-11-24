# WingRiders V2 — swap request

[WingRiders](https://www.wingriders.com/) is an automated market maker on Cardano.
A V2 swap takes two transactions: the user locks a **request** at the V2 request
validator, then a WingRiders agent applies it against the pool and pays the
result to the user ([how a swap works](https://docs.wingriders.com/actions/swapping)).

This interface covers the first transaction only, on one pinned pool:
`place_swap_request` offers ADA to the **ADA/DJED** pool on **mainnet** and asks
for at least a minimum amount of DJED in return. Fulfilment is the agent's
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

The owner signs as the wallet that pays. The request names the owner as both
beneficiary (receives the swap result) and owner (only key that may reclaim).

## Deployment (`mainnet` profile)

| Item | Value |
|---|---|
| Request validator (PlutusV2) | `c134d839a64a5dfb9b155869ef3f34280751a622f69958baa8ffd29c` |
| `RequestScript` party | `addr1w8qnfkpe5e99m7umz4vxnmelxs5qw5dxytmfjk964rla98q605wte` |
| Pool | ADA/DJED, pool validator `af97793b8702f381976cec83e303e9ce17781458c73c4bb16fe02b83` |
| `pool_asset_b_policy` | `8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61` (DJED) |
| `pool_asset_b_name` | `446a65644d6963726f555344` (`DjedMicroUSD`) |
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
| `min_receive` | Int | DJED smallest unit (1 DJED = 1 000 000) | Minimum DJED the agent must pay out. |
| `deadline_ms` | Int | POSIX **milliseconds** | Last moment the agent may apply the request. |

[`invoke-args/place_swap_request.json`](invoke-args/place_swap_request.json)
replays the inputs of the recorded request below. `owner_pkh` and
`owner_stake_key` must be the two halves of `owner`; `min_receive` comes from a
current pool quote; `deadline_ms` must be in the future when you submit.

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

The agent later returns at least `min_receive` DJED plus the `oil` to the
owner and keeps `agent_fee`.

Reference request: mainnet transaction
[`92c25e5e…20e02`](https://cexplorer.io/tx/92c25e5ec64e8c2843d282d4b1c9469e815bf29823b16377fd5040ff06220e02)
(440 040 900 lovelace = 436 040 900 offered + 2 000 000 oil + 2 000 000 agent
fee; minimum 62 220 622 DJED; deadline 1795560969000), applied in
[`57b5303f…336a9`](https://cexplorer.io/tx/57b5303f71e40df66cda31a59cfc105ff8c4f3dd6a2f87e24e5ec1b663c336a9).
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

To build the unsigned transaction from this directory:

```bash
trix invoke --profile mainnet --skip-submit --args-json-path invoke-args/place_swap_request.json
```

The protocol guide, Fluent tools and Skill for this version are linked here
when they are published.

## Checks

`trix check` and `trix build`, then
[`scripts/check-request.py`](../scripts/check-request.py), which decodes the
recorded and the generated request, asserts the effects above, and requires the
[negative fixtures](fixtures/negative/) (deadline in seconds, lost deposit,
reversed direction) to be rejected.

## License

Apache-2.0, see [LICENSE](../LICENSE). The WingRiders contracts this interface
describes are GPL-3.0 and are not copied here.
