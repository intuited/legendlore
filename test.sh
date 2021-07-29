function test {
  echo "python -m doctest $1:";
  python -m doctest "$1";
}
test __init__.py
test predicates.py
test parse.py
test repltools.py
test datatypes.py
test actions.py
test db_analysis/monster_nodes.py
test db_analysis/spell_nodes.py
test util.py
