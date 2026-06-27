"""Core PU/DO sequence combinatorics.

PU/DO sequences contain paired pickup and drop-off events. A sequence is valid
when each pickup appears before its paired drop-off. Already-open drop-offs
represent requests that were picked up before the current planning horizon and
may appear anywhere in the local sequence.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from functools import partial
from math import factorial, prod
from typing import TypeVar

Pickup = TypeVar("Pickup", bound=Hashable)
Event = TypeVar("Event", bound=Hashable)
DropoffFor = Callable[[Pickup], Event]

VALID_STRATEGIES = {"dfs", "insertion", "topological"}


def default_integer_dropoff_for(pickup: int, n_requests: int) -> int:
    """Map pickup ``i`` to drop-off ``i + n_requests``."""

    return pickup + n_requests


def string_dropoff_for(pickup: object) -> str:
    """Map pickup ``x`` to string drop-off label ``x'``."""

    return f"{pickup}'"


def count_fixed_pickup_order_dropoff_insertions(n_requests: int) -> int:
    """Count valid drop-off insertions after fixing one pickup order."""

    _check_non_negative(n_requests, "n_requests")
    return prod(range(1, 2 * n_requests, 2))


def count_open_dropoff_insertions(n_requests: int, n_open_dropoffs: int) -> int:
    """Count ways to insert labeled already-open drop-offs into a PU/DO route."""

    _check_non_negative(n_requests, "n_requests")
    _check_non_negative(n_open_dropoffs, "n_open_dropoffs")
    base_len = 2 * n_requests
    return factorial(base_len + n_open_dropoffs) // factorial(base_len)


def count_pudo_sequences(n_requests: int, n_open_dropoffs: int = 0) -> int:
    """Count valid labeled PU/DO sequences.

    For ``n`` new requests and ``m`` already-open drop-offs, the count is
    ``(2n + m)! / 2**n``.
    """

    _check_non_negative(n_requests, "n_requests")
    _check_non_negative(n_open_dropoffs, "n_open_dropoffs")
    return factorial(2 * n_requests + n_open_dropoffs) // (2**n_requests)


def iter_pudo_sequences(
    requests: Iterable[Pickup],
    *,
    open_dropoffs: Iterable[Event] = (),
    dropoff_for: DropoffFor[Pickup, Event] | None = None,
    strategy: str = "dfs",
) -> Iterator[tuple[Hashable, ...]]:
    """Yield valid pickup/drop-off event sequences.

    Parameters
    ----------
    requests:
        New request pickup labels. Labels must be unique and hashable.
    open_dropoffs:
        Drop-off labels for requests already open before this planning horizon.
        These labels are unconstrained and may appear anywhere in the sequence.
    dropoff_for:
        Function mapping each pickup label to its paired drop-off label. When
        omitted, integer pickups use the default ``pickup + len(requests)``
        convention.
    strategy:
        ``"dfs"`` for dependency-free state-space generation, ``"insertion"``
        for pickup-order/drop-off insertion, or ``"topological"`` for the
        optional NetworkX formulation.
    """

    yield from _iter_pudo_sequences_internal(
        requests,
        open_dropoffs=open_dropoffs,
        dropoff_for=dropoff_for,
        strategy=strategy,
    )


def pudo_sequences(
    requests: Iterable[Pickup],
    *,
    open_dropoffs: Iterable[Event] = (),
    dropoff_for: DropoffFor[Pickup, Event] | None = None,
    strategy: str = "dfs",
) -> list[tuple[Hashable, ...]]:
    """Return valid pickup/drop-off event sequences as a list."""

    return list(
        iter_pudo_sequences(
            requests,
            open_dropoffs=open_dropoffs,
            dropoff_for=dropoff_for,
            strategy=strategy,
        )
    )


def _iter_pudo_sequences_internal(
    requests: Iterable[Pickup],
    *,
    open_dropoffs: Iterable[Event] = (),
    dropoff_for: DropoffFor[Pickup, Event] | None = None,
    strategy: str = "dfs",
    length: int | None = None,
) -> Iterator[tuple[Hashable, ...]]:
    pickups = tuple(requests)
    open_dropoff_tuple = tuple(open_dropoffs)
    selected_length = len(pickups) if length is None else length

    _check_strategy(strategy)
    _check_length(selected_length, len(pickups))
    _check_unique(pickups, "requests")
    _check_unique(open_dropoff_tuple, "open_dropoffs")

    resolved_dropoff_for = _resolve_dropoff_for(pickups, dropoff_for)
    _check_event_label_collisions(pickups, open_dropoff_tuple, resolved_dropoff_for)

    if selected_length == 0:
        yield from itertools.permutations(open_dropoff_tuple)
        return

    if selected_length != len(pickups):
        base_sequences = _iter_pudo_sequences_by_insertion(
            pickups, selected_length, resolved_dropoff_for
        )
        yield from _iter_sequences_with_open_dropoffs_by_insertion(
            base_sequences, open_dropoff_tuple
        )
        return

    if strategy == "dfs":
        yield from _iter_sequences_by_dfs(pickups, open_dropoff_tuple, resolved_dropoff_for)
        return

    if strategy == "insertion":
        base_sequences = _iter_pudo_sequences_by_insertion(
            pickups, selected_length, resolved_dropoff_for
        )
        yield from _iter_sequences_with_open_dropoffs_by_insertion(
            base_sequences, open_dropoff_tuple
        )
        return

    yield from _iter_sequences_by_topological_sort(
        pickups, open_dropoff_tuple, resolved_dropoff_for
    )


def _iter_sequences_by_dfs(
    pickups: tuple[Pickup, ...],
    open_dropoffs: tuple[Event, ...],
    dropoff_for: DropoffFor[Pickup, Event],
) -> Iterator[tuple[Hashable, ...]]:
    dropoffs = tuple(dropoff_for(pickup) for pickup in pickups)
    prefix: list[Hashable] = []
    all_pickups = (1 << len(pickups)) - 1
    all_open_dropoffs = (1 << len(open_dropoffs)) - 1

    def visit(
        remaining_pickups: int,
        onboard_pickups: int,
        remaining_open_dropoffs: int,
    ) -> Iterator[tuple[Hashable, ...]]:
        if (
            remaining_pickups == 0
            and onboard_pickups == 0
            and remaining_open_dropoffs == 0
        ):
            yield tuple(prefix)
            return

        for index, bit in _iter_bits(remaining_pickups):
            prefix.append(pickups[index])
            yield from visit(
                remaining_pickups ^ bit, onboard_pickups | bit, remaining_open_dropoffs
            )
            prefix.pop()

        for index, bit in _iter_bits(onboard_pickups):
            prefix.append(dropoffs[index])
            yield from visit(
                remaining_pickups, onboard_pickups ^ bit, remaining_open_dropoffs
            )
            prefix.pop()

        for index, bit in _iter_bits(remaining_open_dropoffs):
            prefix.append(open_dropoffs[index])
            yield from visit(
                remaining_pickups, onboard_pickups, remaining_open_dropoffs ^ bit
            )
            prefix.pop()

    yield from visit(all_pickups, 0, all_open_dropoffs)


def _iter_pudo_sequences_by_insertion(
    pickups: tuple[Pickup, ...],
    length: int,
    dropoff_for: DropoffFor[Pickup, Event],
) -> Iterator[tuple[Hashable, ...]]:
    for pickup_permutation in itertools.permutations(pickups, length):
        if not pickup_permutation:
            continue

        yield from _iter_dropoff_insertions_for_pickup_order(
            pickup_permutation,
            list(pickup_permutation),
            0,
            dropoff_for,
        )


def _iter_dropoff_insertions_for_pickup_order(
    pickups: tuple[Pickup, ...],
    current_sequence: list[Hashable],
    last_pos_pu: int,
    dropoff_for: DropoffFor[Pickup, Event],
) -> Iterator[tuple[Hashable, ...]]:
    if last_pos_pu == len(pickups):
        yield tuple(current_sequence)
        return

    pickup_position = len(pickups) - last_pos_pu - 1
    pickup_id = pickups[pickup_position]
    dropoff_id = dropoff_for(pickup_id)

    new_sequence = list(current_sequence)
    new_sequence.append(dropoff_id)
    yield from _iter_dropoff_insertions_for_pickup_order(
        pickups,
        new_sequence,
        last_pos_pu + 1,
        dropoff_for,
    )

    for index in range(len(new_sequence) - 1, pickup_position + 1, -1):
        new_sequence[index], new_sequence[index - 1] = (
            new_sequence[index - 1],
            new_sequence[index],
        )
        yield from _iter_dropoff_insertions_for_pickup_order(
            pickups,
            new_sequence,
            last_pos_pu + 1,
            dropoff_for,
        )


def _iter_sequences_with_open_dropoffs_by_insertion(
    base_sequences: Iterable[Sequence[Hashable]],
    open_dropoffs: tuple[Event, ...],
) -> Iterator[tuple[Hashable, ...]]:
    for base_sequence in base_sequences:
        yield from _insert_open_dropoffs(base_sequence, open_dropoffs)


def _insert_open_dropoffs(
    sequence: Sequence[Hashable],
    open_dropoffs: tuple[Event, ...],
) -> Iterator[tuple[Hashable, ...]]:
    stack: list[tuple[list[Hashable], tuple[Event, ...]]] = [
        (list(sequence), tuple(open_dropoffs))
    ]

    while stack:
        current_sequence, remaining_open_dropoffs = stack.pop()
        if not remaining_open_dropoffs:
            yield tuple(current_sequence)
            continue

        dropoff_id = remaining_open_dropoffs[-1]
        new_remaining = remaining_open_dropoffs[:-1]

        for insertion_position in range(len(current_sequence) + 1):
            next_sequence = list(current_sequence)
            next_sequence.insert(insertion_position, dropoff_id)
            stack.append((next_sequence, new_remaining))


def _iter_sequences_by_topological_sort(
    pickups: tuple[Pickup, ...],
    open_dropoffs: tuple[Event, ...],
    dropoff_for: DropoffFor[Pickup, Event],
) -> Iterator[tuple[Hashable, ...]]:
    try:
        import networkx as nx
        from networkx.algorithms.dag import all_topological_sorts
    except ImportError as exc:
        raise ImportError(
            "strategy='topological' requires the optional dependency networkx"
        ) from exc

    graph = nx.DiGraph()
    graph.add_nodes_from(open_dropoffs)

    for pickup in pickups:
        graph.add_edge(pickup, dropoff_for(pickup))

    for sequence in all_topological_sorts(graph):
        yield tuple(sequence)


def _resolve_dropoff_for(
    pickups: tuple[Pickup, ...],
    dropoff_for: DropoffFor[Pickup, Event] | None,
) -> DropoffFor[Pickup, Event]:
    if dropoff_for is None:
        return partial(default_integer_dropoff_for, n_requests=len(pickups))
    return dropoff_for


def _generated_dropoffs(
    pickups: tuple[Pickup, ...],
    dropoff_for: DropoffFor[Pickup, Event],
) -> tuple[Hashable, ...]:
    try:
        return tuple(dropoff_for(pickup) for pickup in pickups)
    except TypeError as exc:
        raise TypeError(
            "dropoff_for must be provided when pickup labels do not support "
            "the default integer mapping"
        ) from exc


def _check_event_label_collisions(
    pickups: tuple[Pickup, ...],
    open_dropoffs: tuple[Event, ...],
    dropoff_for: DropoffFor[Pickup, Event],
) -> None:
    dropoffs = _generated_dropoffs(pickups, dropoff_for)
    _check_unique(dropoffs, "generated drop-off labels")

    pickup_set = set(pickups)
    dropoff_set = set(dropoffs)
    open_dropoff_set = set(open_dropoffs)

    pickup_dropoff_overlap = pickup_set.intersection(dropoff_set)
    if pickup_dropoff_overlap:
        raise ValueError(
            "pickup labels and generated drop-off labels must be distinct; "
            f"overlap: {pickup_dropoff_overlap!r}"
        )

    open_overlap = open_dropoff_set.intersection(pickup_set.union(dropoff_set))
    if open_overlap:
        raise ValueError(
            "open_dropoffs must be distinct from pickup and generated drop-off "
            f"labels; overlap: {open_overlap!r}"
        )


def _check_unique(values: tuple[Hashable, ...], name: str) -> None:
    seen: set[Hashable] = set()
    for value in values:
        try:
            already_seen = value in seen
        except TypeError as exc:
            raise TypeError(f"{name} must contain hashable labels") from exc

        if already_seen:
            raise ValueError(f"{name} must contain unique labels; duplicate: {value!r}")

        seen.add(value)


def _check_strategy(strategy: str) -> None:
    if strategy not in VALID_STRATEGIES:
        choices = "', '".join(sorted(VALID_STRATEGIES))
        raise ValueError(f"strategy must be one of '{choices}'")


def _check_length(length: int, n_requests: int) -> None:
    if length < 0:
        raise ValueError("length must be non-negative")
    if length > n_requests:
        raise ValueError("length cannot exceed the number of requests")


def _check_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _iter_bits(mask: int) -> Iterator[tuple[int, int]]:
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1, bit
        mask ^= bit
