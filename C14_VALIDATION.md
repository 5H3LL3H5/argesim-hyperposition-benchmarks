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

## Historical run output

We executed 100 Monte Carlo runs (with randomized seeds) to compare the performance for Distributor D1 across the three strategies.

**Summary of D1 Metrics:**

| Strategy        | Metric (C/N/R) | Mean    | Dev    | Min     | Max     |
|-----------------|----------------|---------|--------|---------|---------|
| Strategy A      | C (Total Cost) | 58658.92 | 159.31 | 58210.00 | 59044.00 |
|                 | N (Delivered)  | 227.42   | 12.82  | 191.00   | 257.00   |
|                 | R (Cost/Item)  | 258.81   | 15.72  | 226.50   | 309.09   |
| Strategy B      | C (Total Cost) | 32695.98 | 1374.35| 29759.00 | 35866.00 |
|                 | N (Delivered)  | 227.42   | 12.82  | 191.00   | 257.00   |
|                 | R (Cost/Item)  | 143.97   | 5.36   | 127.76   | 158.90   |
| Strategy C      | C (Total Cost) | 26344.58 | 1084.10| 23879.00 | 28869.00 |
|                 | N (Delivered)  | 227.42   | 12.82  | 191.00   | 257.00   |
|                 | R (Cost/Item)  | 116.01   | 4.40   | 104.98   | 131.15   |

The table was generated with seed 42 and 100 runs after applying the official
Table 3 mappings and lead-time-weighted transport costs.

### Trajectory Plot
A trajectory plot illustrating the total stock of Distributor D1 over the 30-day period (for Task A1) has been generated using `numpy` and `matplotlib` and is available at `c14_trajectory.png`.

## Evidence boundary

The committed conformance tests cover the official product/factory table, the
independent uniform wholesaler choices, all-or-nothing orders, lead-time-weighted
transport cost, and the 720-hour horizon. The numerical table above is retained
as historical run output and must be regenerated after model changes; it is not
an independent validation data set. C14 therefore remains `implemented` rather
than `validated`.
