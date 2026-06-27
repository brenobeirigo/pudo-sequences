from pudo_sequences.index import _PrefixTrie


def test_internal_prefix_trie_stores_sequences_and_continuations():
    trie = _PrefixTrie()
    trie.add_sequences([(1,), (1, 2, 3), (1, 4), (2, 5)])

    assert trie.get_all_sequences_from_tree() == {
        (1,),
        (1, 2, 3),
        (1, 4),
        (2, 5),
    }
    assert trie.continuations([1]) == {(), (2, 3), (4,)}
    assert trie.continuations([9]) == set()
