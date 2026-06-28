# pudo-sequences

Generate valid PU/DO action spaces for small route insertion problems.

`pudo-sequences` is a small Python package for pickup/drop-off sequence
combinatorics. It counts, generates, streams, and indexes event orders where
each pickup appears before its paired drop-off.

```text
pickup_i before dropoff_i
```

Use it as the first feasibility layer in dispatching, routing, simulation,
optimization, or learning code. For a small local insertion problem, generate
all PU/DO-valid event orders first. Then your application can test the classic
DARP layers: capacity, customer time windows, vehicle load, travel cost, energy
cost, or reward.

## Why It Matters

An event order is not just a permutation. With four new requests there are eight
events:

```text
0 1 2 3 = pickups
4 5 6 7 = paired drop-offs
```

Normal permutations produce:

```text
8! = 40,320 event orders
```

Most of those orders are impossible because at least one drop-off appears before
its pickup. PU/DO precedence leaves:

```text
40,320 / 2^4 = 2,520 valid event orders
```

That is the gap this package fills: it gives you the constrained action space
directly instead of making you generate unrestricted permutations and filter
them afterward.

For a tiny two-request example:

```python
from itertools import permutations

from pudo_sequences import pudo_sequences

all_orders = list(permutations([0, 1, 2, 3]))
valid_orders = pudo_sequences([0, 1])

print(len(all_orders))
print(len(valid_orders))
```

```text
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

With the default integer convention, pickup `i` maps to drop-off `i + n`, where
`n` is the number of new requests.

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

Materialize the complete action set when it is small:

```python
from pudo_sequences import count_pudo_sequences, pudo_sequences

routes = pudo_sequences([0, 1])

assert count_pudo_sequences(2) == 6
assert routes[0] == (0, 1, 2, 3)
```

Stream routes when you want to score candidates one at a time:

```python
from pudo_sequences import iter_pudo_sequences

best_route = None
best_score = float("inf")

for route in iter_pudo_sequences([0, 1, 2]):
    score = sum(route)  # Replace with capacity, time-window, or cost logic.
    if score < best_score:
        best_route = route
        best_score = score
```

## Open Drop-Offs

Some local plans start with passengers, parcels, or tasks already onboard.
Their pickups happened before the current sequence, so only their drop-offs
appear. These already-open drop-offs may be inserted anywhere.

```python
from pudo_sequences import count_pudo_sequences, pudo_sequences

routes = pudo_sequences([0, 1], open_dropoffs=[4])

assert len(routes) == count_pudo_sequences(2, n_open_dropoffs=1)
assert len(routes) == 30
assert (4, 0, 1, 2, 3) in routes
assert (0, 1, 2, 3, 4) in routes
```

## Custom Labels

Use `dropoff_for` when labels are not the default integer convention.

```python
from pudo_sequences import pudo_sequences

routes = pudo_sequences(
    [1, 2],
    dropoff_for=lambda pickup: f"{pickup}'",
)

assert (1, "1'", 2, "2'") in routes
```

The labels only need to be unique and hashable.

## Counts

For `n` labeled pickup/drop-off pairs, the number of valid sequences is:

```text
(2n)! / 2^n
```

With `m` already-open drop-offs:

```text
(2n + m)! / 2^n
```

The constructive view is:

```text
1. choose a pickup order;
2. insert each paired drop-off only after its pickup;
3. optionally insert already-open drop-offs anywhere.
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

## Prefix Indexing

When a caller repeatedly asks for valid continuations after a partial route,
build a prefix index once and reuse it.

```python
from pudo_sequences import build_pudo_index

index = build_pudo_index([0, 1])

assert index.continuations([0, 1]) == {(2, 3), (3, 2)}
assert index.continuations([0, 2]) == {(1, 3)}
```

For example, after prefix `[0, 2]`, request `0` has been picked up and dropped
off. The only remaining valid suffix is pickup `1` followed by drop-off `3`.

## Generation Strategies

The default strategy is dependency-free DFS over the PU/DO state space.

Other strategies are available for teaching and comparison:

- `strategy="insertion"`: generate pickup orders, then insert each paired
  drop-off only after its pickup.
- `strategy="topological"`: use NetworkX to enumerate all topological orders of
  a precedence graph with edges `pickup_i -> dropoff_i`.

All strategies represent the same constrained sequence set.

```python
from pudo_sequences import pudo_sequences

dfs_routes = set(pudo_sequences([0, 1, 2], strategy="dfs"))
insertion_routes = set(pudo_sequences([0, 1, 2], strategy="insertion"))

assert dfs_routes == insertion_routes
```

Full enumeration grows factorially. This package is intended for small local
neighborhoods, exact validation, teaching, and candidate insertion sets inside a
larger dispatch, optimization, or learning system.

## Development

```bash
pip install -e ".[dev]"
pytest -q
python -m build --sdist --wheel
python -m twine check dist/*
```
