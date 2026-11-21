# C14 supply-chain implementation and reference variants

C14 models four factories, four distributors and twelve products. It runs for
30 days. Each factory draws exponential production intervals with mean 600 s,
rounded down to whole seconds with a minimum of one second. The distributors
order ten units of each product at the start of day eight. Wholesale demand
starts at the start of day nine, then recurs at integer intervals uniformly
distributed from 600 to 3,600 s. Delivery takes 12–22 hours, depending on the
factory/distributor pair. Storage costs €1 per unit per day and transport costs
€10 per delivery-hour per filled product order. [Model and task functions](../argesim_benchmarks/models/c14_supply_chain.py)

| Registered tasks | Quantity reported |
|---|---|
| `A1`, `B1` | Daily stock snapshots for distributor D1 under fixed-quantity or prior-day demand ordering. |
| `A2`, `B2`, `C1` | D1 cost, units delivered and cost per unit across 100 runs by default. Strategy C places prior-day demand with the fastest eligible factory able to fill the order. |
| `C2` | Comparison of all three strategies for D1 using the same seed schedule. |

## D1 over 100 replications

Demand windows run from midnight up to the following midnight. A wholesale order at exactly midnight contributes to the new day's total. Daily transport charges apply per fulfilled distributor/factory/product order, regardless of quantity.

The definition states that Task A orders two units of each product every day. A published MATLAB solution orders two units only for a product sold during the past day. Both policies add unfilled wholesale demand and use the same day-eight initial supply. `every-product` is the default. The optional `sold-products` argument makes the published ordering rule reproducible. [Definition](https://www.argesim.org/benchmarks/c14) · [MATLAB, section 3](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_28_1/articles/sne.28.1.10407.bn14.OA.pdf)

Seed 42 selects the same 100 replication seeds for each row. Values in parentheses are sample standard deviations. R is averaged from per-run C/N.

| Policy | Cost C (€) | Delivered N | Relative cost R (€/unit) |
|---|---:|---:|---:|
| Strategy A | 58,659.07 (159.29) | 227.42 (12.82) | 258.81 (15.72) |
| Strategy B | 32,673.78 (1,372.27) | 227.42 (12.82) | 143.88 (5.40) |
| Strategy C | 26,807.78 (1,080.73) | 227.42 (12.82) | 118.06 (4.50) |
| Strategy A (sold-products) | 33,515.35 (1,425.34) | 227.42 (12.82) | 147.59 (5.92) |

AutoMod reports mean costs of €33,157, €32,698 and €26,364 for A/B/C. The `sold-products` comparison gives €33,515, €32,674 and €26,808. The default literal Task A gives €58,659. The publications do not establish common order books or identical accounting across their models. C14 retains the `implemented` gate. [AutoMod results](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C14/C14-solution-AutoMod.pdf)

```sh
python -m argesim_benchmarks run C14 C2
python -m argesim_benchmarks run C14 C2 --kwargs-json '{"simple_order_policy":"sold-products"}'
```
