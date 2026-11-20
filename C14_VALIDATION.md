# ARGESIM C14 Supply Chain Implementation Report

## Experiment

The C14 Supply Chain benchmark focuses on discrete-time modeling of a supply chain process, specifically evaluating different ordering strategies and their impact on system performance and costs. The benchmark involves 4 factories, 4 distributors, and a group of wholesalers trading 12 products.

The experiments conducted correspond to the official task definitions:
- **Task A (Simple Strategy)**: Distributors daily order a constant 2 pieces per product from fixed factories.
- **Task B (On-Demand Strategy)**: Distributors order exactly what the wholesalers ordered in the previous 24 hours.
- **Task C (Minimal Supply Time Strategy)**: Distributors order dynamically based on the factory offering the shortest lead time.

## Initial Parameters
- **Time Horizon**: 30 days (720 hours).
- **Factory Interarrival**: Exponential with mean = 600s.
- **Wholesaler Demand**: Uniform distribution between [600, 3600]s.
- **Lead Times**: Configured matrix between distributors and factories (12h to 22h).
- **Costs**: Transport = 10 Euro per delivery-hour per order (regardless of quantity), Storage = 1 Euro per product per day.

## D1 over 100 replications

Demand windows run from midnight up to the following midnight. A wholesale order at exactly midnight contributes to the new day's total. Daily transport charges apply per fulfilled distributor/factory/product order, regardless of quantity.

The definition states that Task A orders two units of each product every day. A published MATLAB solution orders two units only for a product sold during the past day. Both policies add unfilled wholesale demand and use the same day-eight initial supply. `every-product` is the default. The optional `sold-products` argument makes the published ordering rule reproducible. [Definition](https://www.argesim.org/benchmarks/c14) · [MATLAB, section 3](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_28_1/articles/sne.28.1.10407.bn14.OA.pdf)

Seed 42 generates the same 100 workloads for each row. Values in parentheses are sample standard deviations. R is averaged from per-run C/N.

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
