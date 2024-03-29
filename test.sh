#!/bin/bash
# Test script that just runs doctests on all applicable files.

function test {
  echo "python -m doctest $1:";
  python -m doctest "$1";
}
test db_items.py
test collection.py
test predicates.py
test parse.py
test repltools.py
test datatypes.py
test actions.py
test db_analysis/monster_nodes.py
test db_analysis/spell_nodes.py
test util.py
test README.md
