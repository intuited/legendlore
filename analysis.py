import dnd5edb
from collections import Counter
from pprint import pprint, pformat
from functools import partial
import statistics

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

def analyze_fey(tree=None):
    """Breakdown of Fey monsters in 5e."""
    if not tree:
        tree = dnd5edb.DB.get_tree()
    fey = [m for m in dnd5edb.Monsters() if m.type.startswith('fey')]
    print(f'Number of fey monsters: {len(fey)}')

    as_names = ['str', 'dex', 'con', 'int', 'wis', 'cha']
    stats = {'min': min,
             'avg': statistics.mean,
             'std': statistics.stdev,
             'max': max}
    print(fntab(fey, as_names, getattr, stats))

    print('how do save bonuses work?  Are they added to AS bonuses or do they replace them?')
    flatten = lambda lists: [i for l in lists for i in l]
    headers = ['name', 'cr'] + flatten([ascore, f'{ascore} save'] for ascore in as_names)
    def msave(m, stat):
        if hasattr(m, 'saves'):
            return m.saves.get(stat, '-')
        else:
            return '-'
    row_items = lambda m: [m.name, m.cr] + flatten([getattr(m, ascore), msave(m, ascore)] for ascore in as_names)
    data = [headers] + [row_items(m) for m in fey]
    print('\n'.join(tabular(data)))

def fntab(db, rows, datagetter, fns):
    """Runs aggregate functions `fns` on values from the db

    `rows`: list of db fields or subfields
    `datagetter`: takes monster and item from `rows`, returns datum
    `fns`: {column_header: transformation_function}
    """
    data = [ [datagetter(entry, item) for entry in db] for item in rows ]
    calculate = lambda vals: (fn(vals) for fn in fns.values())
    results = [ list(fns.keys()) ] + [calculate(vals) for vals in data]
    results = [ [''] + rows ] + list(zip(*results))
    results = list(zip(*results))

    return '\n'.join(tabular(results))

def tabular(rows):
    """`rows` is a list of lists of strings.

    Yields strings containing lines of tabular data.
    """
    widths = [max(map(len, map(str, col))) for col in zip(*rows)]
    for row in rows:
        yield "  ".join((str(val).ljust(width) for val, width in zip(row, widths)))
