# C08 canal-and-lock validation

C08 reaches `validated` against five deterministic datasets from the definition appendix. The gate covers directional admissions and transit times. The implementation also provides the stochastic Task C variance-reduction experiments. [Definition and solutions](https://www.argesim.org/benchmarks/c08/) · [Model](../argesim_benchmarks/models/c08_canal_and_lock.py)

| Appendix case | Regression observable |
|---|---|
| 1 | Alternating single-barge cycles take 54 minutes per barge. |
| 2 | Batches of two eastbound and three westbound barges average 71 and 88 minutes, respectively. |
| 3 and 4 | East-only and west-only traffic retain the 54-minute transit. |
| 5 | Mixed consecutive cycles average 94.67 minutes eastbound and 130 minutes westbound. |

A directional cycle counts cumulative admissions. A departure from a cycle that has reached its limit does not free a place in that cycle. Task C tests cover ordinary and antithetic 90% intervals, independent and common-random-number comparisons, and the hypothesis decision. [Regression cases](../tests/test_argesim_c08.py)

```sh
python -m unittest discover -s tests -p test_argesim_c08.py -v
```
