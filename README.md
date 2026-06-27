# pudo-sequences

`pudo-sequences` is a small Python package for PU/DO constrained sequence
combinatorics: counting, generating, and indexing event orders where every
pickup must occur before its paired drop-off.

```text
pickup_i before dropoff_i
```

Use it when a routing, ridesharing, dispatching, simulation, optimization, or
learning system needs to reason about feasible local service orders before
evaluating distance, time windows, capacity, cost, or reward.

## Why It Matters

A PU/DO route is not just a permutation of events. For two new requests, the
four events are:

```text
0 = pickup request 0
1 = pickup request 1
2 = drop-off request 0
3 = drop-off request 1
```

`itertools.permutations` returns all `24` event orders, including impossible
orders such as `(2, 0, 1, 3)`, where request `0` is dropped off before it is
picked up.

```python
from itertools import permutations

from pudo_sequences import pudo_sequences

all_orders = list(permutations([0, 1, 2, 3]))
valid_orders = pudo_sequences([0, 1])

print(len(all_orders))
print(len(valid_orders))
```

```python
24
6
```

The valid orders are:

```python
[
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 2, 1, 3),
    (1, 0, 2, 3),
    (1, 0, 3, 2),
    (1, 3, 0, 2),
]
```

You can filter normal permutations yourself:

```python
def is_valid(route):
    return route.index(0) < route.index(2) and route.index(1) < route.index(3)


filtered = [route for route in all_orders if is_valid(route)]

assert filtered == valid_orders
```

For small teaching examples that is fine. In real local-search or learning
loops, generating impossible actions first adds noise and waste. The gap grows
quickly:

| Requests | Unconstrained permutations | Valid PU/DO sequences | Valid share |
| ---: | ---: | ---: | ---: |
| 1 | 2 | 1 | 50.0% |
| 2 | 24 | 6 | 25.0% |
| 3 | 720 | 90 | 12.5% |
| 4 | 40,320 | 2,520 | 6.25% |
| 5 | 3,628,800 | 113,400 | 3.125% |

The package focuses on this first layer:

```text
PU/DO combinatorics: which event orders are logically possible?
Domain evaluation: which of those orders satisfy time, capacity, or cost rules?
Selection: which feasible order should the system choose?
```

It is not a routing solver. It gives you the constrained local sequence space
that a solver, simulator, heuristic, or policy can evaluate.

## Install

```bash
pip install pudo-sequences
```

For local development:

```bash
pip install -e ".[dev]"
pytest
```

The core package has no runtime dependency beyond Python. The optional
`topological` strategy requires NetworkX:

```bash
pip install "pudo-sequences[networkx]"
```

## Quick Start

```python
from pudo_sequences import count_pudo_sequences, pudo_sequences

print(count_pudo_sequences(2))
print(pudo_sequences([0, 1]))
```

With the default integer convention, pickup `i` maps to drop-off `i + n`, where
`n` is the number of requests. For `requests=[0, 1]`, drop-offs are `2` and
`3`.

To stream instead of materializing every route:

```python
from pudo_sequences import iter_pudo_sequences

best_route = None
best_score = float("inf")

for route in iter_pudo_sequences([0, 1, 2]):
    score = sum(route)  # Replace with distance, time, reward, or feasibility logic.
    if score < best_score:
        best_route = route
        best_score = score
```

To check whether a candidate from a heuristic is PU/DO-valid, compare it with
the generated local action set for small neighborhoods:

```python
from pudo_sequences import pudo_sequences

valid_routes = set(pudo_sequences([0, 1, 2]))

assert (0, 3, 1, 4, 2, 5) in valid_routes
assert (3, 0, 1, 4, 2, 5) not in valid_routes
```

## Custom Labels

Use `dropoff_for` when events are not integers:

```python
from pudo_sequences import pudo_sequences

routes = pudo_sequences(
    ["alice", "bob"],
    dropoff_for=lambda pickup: ("dropoff", pickup),
)

assert (
    "alice",
    ("dropoff", "alice"),
    "bob",
    ("dropoff", "bob"),
) in routes
```

By requiring a mapping from pickup labels to drop-off labels, the package can
use the same combinatorics for rider IDs, job IDs, task names, tuples, or other
hashable labels.

## Already-Open Drop-Offs

Sometimes a planning horizon starts with requests already onboard. Their
drop-offs have no pickup inside the local sequence, so they may appear anywhere.

```python
from pudo_sequences import count_pudo_sequences, pudo_sequences

routes = pudo_sequences([0, 1], open_dropoffs=[4])

assert len(routes) == count_pudo_sequences(2, n_open_dropoffs=1)
assert len(routes) == 30
assert (4, 0, 1, 2, 3) in routes
assert (0, 1, 2, 3, 4) in routes
```

This represents two new requests plus one already-open request whose drop-off
is `4`.

## Counts

For `n` labeled pickup/drop-off pairs, the number of valid sequences is:

```text
(2n)! / 2^n
```

Equivalently:

```text
n! * (1 * 3 * 5 * ... * (2n - 1))
```

If there are also `m` already-open drop-offs, the count becomes:

```text
(2n + m)! / 2^n
```

API:

```python
from pudo_sequences import (
    count_fixed_pickup_order_dropoff_insertions,
    count_open_dropoff_insertions,
    count_pudo_sequences,
)

assert count_pudo_sequences(3) == 90
assert count_pudo_sequences(3, n_open_dropoffs=2) == 5040
assert count_fixed_pickup_order_dropoff_insertions(3) == 15
assert count_open_dropoff_insertions(3, 2) == 56
```

The constructive count is useful for explaining the structure:

```text
1. choose a pickup order;
2. insert each paired drop-off only after its pickup;
3. optionally insert already-open drop-offs anywhere.
```

## Generation Strategies

The default strategy is dependency-free DFS over the PU/DO state space:

```python
from pudo_sequences import iter_pudo_sequences

for route in iter_pudo_sequences([0, 1, 2], strategy="dfs"):
    pass
```

Other strategies are available for comparison:

- `strategy="insertion"`: generate pickup orders, then insert each paired
  drop-off only after its pickup.
- `strategy="topological"`: use NetworkX to enumerate all topological orders of
  a precedence graph with edges `pickup_i -> dropoff_i`.

For `n=3`, all strategies represent the same constrained sequence set:

```python
from pudo_sequences import pudo_sequences

dfs_routes = set(pudo_sequences([0, 1, 2], strategy="dfs"))
insertion_routes = set(pudo_sequences([0, 1, 2], strategy="insertion"))

assert dfs_routes == insertion_routes
```

The generator is intended for small local neighborhoods. PU/DO sequence counts
grow factorially, so large request sets should usually be handled by heuristics,
optimization models, or sampling rather than full enumeration.

## Prefix Indexing

When a caller repeatedly asks for valid continuations after a partial route,
build a prefix index:

```python
from pudo_sequences import build_pudo_index

index = build_pudo_index([0, 1])

assert index.continuations([0, 1]) == {(2, 3), (3, 2)}
assert index.continuations([0, 2]) == {(1, 3)}
```

The index is a secondary feature. Its purpose is fast continuation lookup, not
the definition of the package.

## Development

```bash
pip install -e ".[dev]"
pytest -q
python -m build --sdist --wheel
python -m twine check dist/*
```
