"""Prefix indexing for PU/DO sequence continuations."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator, Sequence
from typing import TypeAlias

from .core import DropoffFor, iter_pudo_sequences

Node: TypeAlias = dict[Hashable | None, "Node"]


class _PrefixTrie:
    """Small trie for hashable event sequences."""

    terminal = None

    def __init__(self, sequences: Iterable[Sequence[Hashable]] | None = None):
        self.tree: Node = {}
        if sequences is not None:
            self.add_sequences(sequences)

    @classmethod
    def from_sequences(cls, sequences: Iterable[Sequence[Hashable]]) -> "_PrefixTrie":
        return cls(sequences)

    def add_entry(self, sequence: Sequence[Hashable]) -> None:
        tree = self.tree
        for node in sequence:
            tree = tree.setdefault(node, {})
        tree[self.terminal] = {}

    def add_sequences(self, sequences: Iterable[Sequence[Hashable]]) -> None:
        for sequence in sequences:
            self.add_entry(sequence)

    def iter_sequences(self, tree: Node | None = None) -> Iterator[tuple[Hashable, ...]]:
        start = self.tree if tree is None else tree
        yield from self._iter_sequences_from_node(start, [])

    def get_all_sequences_from_tree(
        self, tree: Node | None = None
    ) -> set[tuple[Hashable, ...]]:
        return set(self.iter_sequences(tree))

    def get_tree_starts_with_sequence(self, sequence: Sequence[Hashable]) -> Node:
        tree = self.tree
        for node in sequence:
            if node not in tree:
                return {}
            tree = tree[node]
        return tree

    def starts_with_sequence(self, sequence: Sequence[Hashable]) -> set[tuple[Hashable, ...]]:
        return self.get_all_sequences_from_tree(self.get_tree_starts_with_sequence(sequence))

    def continuations(self, prefix: Sequence[Hashable]) -> set[tuple[Hashable, ...]]:
        return self.starts_with_sequence(prefix)

    def _iter_sequences_from_node(
        self, tree: Node, prefix: list[Hashable]
    ) -> Iterator[tuple[Hashable, ...]]:
        for node, sub_tree in tree.items():
            if node is self.terminal:
                yield tuple(prefix)
                continue

            prefix.append(node)
            yield from self._iter_sequences_from_node(sub_tree, prefix)
            prefix.pop()

    def __str__(self) -> str:
        return "{" + ",".join(map(str, self.get_all_sequences_from_tree())) + "}"

    def __repr__(self) -> str:
        return self.__str__()


class PudoSequenceIndex:
    """Prefix index over complete PU/DO sequences.

    Build an index when a caller repeatedly asks which valid suffixes remain
    after a partial event prefix.
    """

    def __init__(self, sequences: Iterable[Sequence[Hashable]]):
        self._trie = _PrefixTrie(sequences)

    @classmethod
    def from_sequences(
        cls, sequences: Iterable[Sequence[Hashable]]
    ) -> "PudoSequenceIndex":
        return cls(sequences)

    def iter_sequences(self) -> Iterator[tuple[Hashable, ...]]:
        """Yield every complete sequence stored in the index."""

        yield from self._trie.iter_sequences()

    def sequences(self) -> set[tuple[Hashable, ...]]:
        """Return every complete sequence stored in the index."""

        return set(self.iter_sequences())

    def continuations(self, prefix: Sequence[Hashable]) -> set[tuple[Hashable, ...]]:
        """Return suffixes that complete ``prefix`` into a valid sequence."""

        return self._trie.continuations(prefix)


def build_pudo_index(
    requests: Iterable[Hashable],
    *,
    open_dropoffs: Iterable[Hashable] = (),
    dropoff_for: DropoffFor | None = None,
    strategy: str = "dfs",
) -> PudoSequenceIndex:
    """Build a prefix index for valid PU/DO sequences."""

    return PudoSequenceIndex(
        iter_pudo_sequences(
            requests,
            open_dropoffs=open_dropoffs,
            dropoff_for=dropoff_for,
            strategy=strategy,
        )
    )
