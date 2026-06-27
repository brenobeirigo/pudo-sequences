import math

import pytest

from pudo_sequences import (
    PudoSequenceIndex,
    build_pudo_index,
    count_fixed_pickup_order_dropoff_insertions,
    count_open_dropoff_insertions,
    count_pudo_sequences,
    iter_pudo_sequences,
    pudo_sequences,
)


def test_pudo_counts_with_and_without_open_dropoffs():
    for n_requests in range(0, 7):
        assert count_pudo_sequences(n_requests) == math.factorial(
            2 * n_requests
        ) // (2**n_requests)

    for n_requests in range(0, 5):
        for n_open_dropoffs in range(0, 4):
            assert count_pudo_sequences(n_requests, n_open_dropoffs) == math.factorial(
                2 * n_requests + n_open_dropoffs
            ) // (2**n_requests)
            assert count_open_dropoff_insertions(
                n_requests, n_open_dropoffs
            ) == math.factorial(2 * n_requests + n_open_dropoffs) // math.factorial(
                2 * n_requests
            )

    assert count_fixed_pickup_order_dropoff_insertions(3) == 15


def test_default_integer_sequence_generation():
    assert pudo_sequences([0, 1]) == [
        (0, 1, 2, 3),
        (0, 1, 3, 2),
        (0, 2, 1, 3),
        (1, 0, 2, 3),
        (1, 0, 3, 2),
        (1, 3, 0, 2),
    ]


def test_open_dropoff_generation_matches_count():
    routes = set(pudo_sequences([0, 1], open_dropoffs=[4]))

    assert len(routes) == count_pudo_sequences(2, n_open_dropoffs=1)
    assert len(routes) == 30
    assert (4, 0, 1, 2, 3) in routes
    assert (0, 1, 2, 3, 4) in routes


def test_only_open_dropoffs_generate_all_permutations():
    assert set(pudo_sequences([], open_dropoffs=[10, 11])) == {
        (10, 11),
        (11, 10),
    }


def test_custom_hashable_labels_require_dropoff_mapping():
    with pytest.raises(TypeError):
        pudo_sequences(["alice", "bob"])

    routes = set(
        iter_pudo_sequences(
            ["alice", "bob"],
            dropoff_for=lambda pickup: ("dropoff", pickup),
        )
    )

    assert len(routes) == 6
    assert ("alice", ("dropoff", "alice"), "bob", ("dropoff", "bob")) in routes


def test_generation_strategies_are_equivalent():
    requests = (0, 1, 2)
    dfs_routes = set(pudo_sequences(requests, strategy="dfs"))
    insertion_routes = set(pudo_sequences(requests, strategy="insertion"))

    assert dfs_routes == insertion_routes
    assert len(dfs_routes) == count_pudo_sequences(3)


def test_topological_strategy_matches_domain_generators_when_networkx_is_available():
    pytest.importorskip("networkx")

    requests = (0, 1, 2)
    topological_routes = set(pudo_sequences(requests, strategy="topological"))
    dfs_routes = set(pudo_sequences(requests, strategy="dfs"))

    assert topological_routes == dfs_routes


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        pudo_sequences([0, 0])

    with pytest.raises(ValueError):
        pudo_sequences([0], open_dropoffs=[2, 2])

    with pytest.raises(ValueError):
        pudo_sequences([0, 1], open_dropoffs=[2])

    with pytest.raises(ValueError):
        pudo_sequences([0, 1], dropoff_for=lambda pickup: pickup)

    with pytest.raises(ValueError):
        pudo_sequences([0, 1], strategy="unknown")

    with pytest.raises(ValueError):
        count_pudo_sequences(-1)


def test_pudo_sequence_index_continuations_for_partial_route():
    index = build_pudo_index([0, 1])

    assert isinstance(index, PudoSequenceIndex)
    assert index.continuations([0, 1]) == {(2, 3), (3, 2)}
    assert index.continuations([0, 2]) == {(1, 3)}
    assert index.continuations([1, 3]) == {(0, 2)}
    assert index.continuations([3]) == set()


def test_pudo_sequence_index_from_sequences():
    index = PudoSequenceIndex.from_sequences([(1, 2), (1, 3)])

    assert index.sequences() == {(1, 2), (1, 3)}
    assert index.continuations([1]) == {(2,), (3,)}

