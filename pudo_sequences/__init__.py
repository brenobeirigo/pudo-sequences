"""PU/DO constrained sequence combinatorics."""

from .core import (
    count_fixed_pickup_order_dropoff_insertions,
    count_open_dropoff_insertions,
    count_pudo_sequences,
    iter_pudo_sequences,
    pudo_sequences,
)
from .index import PudoSequenceIndex, build_pudo_index

__all__ = [
    "PudoSequenceIndex",
    "build_pudo_index",
    "count_fixed_pickup_order_dropoff_insertions",
    "count_open_dropoff_insertions",
    "count_pudo_sequences",
    "iter_pudo_sequences",
    "pudo_sequences",
]

__version__ = "0.1.0"
