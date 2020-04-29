import dnd5edb
from collections import Counter
from pprint import pprint, pformat
from functools import partial

pprint = partial(pprint, indent=2, width=100)
pformat = partial(pformat, indent=2, width=100)

def indent(text, depth=4):
    return '\n'.join(' '*depth + line for line in text.split("\n"))

def analyze_monster_nodes(tree=None):
    """Output a bunch of info about the monster nodes in the DB."""
    if not tree:
        tree = dnd5edb.DB.get_tree()
    monsters = tree.xpath('//monster')
    print(f"Monster node count: {len(monsters)}")
    subnodecounts = Counter(n.tag for n in tree.xpath('//monster/*'))
    print(f"Tag counts: {subnodecounts}")

    for tag in subnodecounts:
        nodes = tree.xpath('//monster/' + tag)
        print(f"{tag}: {len(nodes)} nodes")
        valuecounts = Counter(n.text for n in nodes)
        def fmt(pair, length=80):
            return (str(pair[0])[:length], pair[1])
        def fmt_all(values, length=80):
            return indent(pformat([fmt(pair) for pair in values]))
        if len(valuecounts) > 1000:
            print(f"  {len(valuecounts)} unique values.  Top Ten:")
            print(fmt_all(valuecounts.most_common(10)))
        else:
            print(f"  {len(valuecounts)} unique values:")
            print(fmt_all(valuecounts.items()))
