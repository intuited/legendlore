import dnd5edb
from collections import Counter
from pprint import pprint, pformat
from functools import partial
import statistics

pprint = partial(pprint, indent=2, width=100)
pformat = partial(pformat, indent=2, width=100)

def indent(text, prefix='    '):
    return '\n'.join(prefix + line for line in text.split("\n"))

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
    headers = ['name', 'cr', 'ac', 'hp'] + flatten([ascore, f'{ascore} save'] for ascore in as_names)
    def msave(m, stat):
        if hasattr(m, 'saves'):
            return m.saves.get(stat, '-')
        else:
            return '-'
    row_items = lambda m: [m.name, m.cr, getattr(m, 'ac_num', '-'), m.hp] + flatten([getattr(m, ascore), msave(m, ascore)] for ascore in as_names)
    data = [headers] + [row_items(m) for m in fey]
    #print('\n'.join(tabular(data)))
    print('\n'.join(csv(data)))

    print('Fey spells/slots:')
    fey = sorted(fey, key=lambda m: m.cr)
    for m in fey:
        if hasattr(m, 'spells'):
            print(f"- {m.name} (CR {m.cr}): [{m.spells}]; slots: {getattr(m, 'slots', 'N/A')}")

    spells = Counter(flatten(m.spells.split(', ') for m in fey if hasattr(m, 'spells')))
    print('Number of fey with each spell:')
    print('\n'.join(f'{s}, {f}' for s, f in spells.items()))

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

def csv(rows):
    yield from (', '.join(map(str, row)) for row in rows)

def tabular(rows):
    """`rows` is a list of lists of strings.

    Yields strings containing lines of tabular data.
    """
    widths = [max(map(len, map(str, col))) for col in zip(*rows)]
    for row in rows:
        yield "  ".join((str(val).ljust(width) for val, width in zip(row, widths)))

def knowledge_cleric_spells(tree=None):
    """Prints one-line summaries of knowledge cleric spells."""
    spells = dnd5edb.DB.get_spells()

    cleric_spells = (spell for spell in spells
                     if 'Cleric' in spell['classes']
                     or 'Cleric (Knowledge)' in spell['classes'])

    cleric_spells = sorted(cleric_spells, key=lambda s: s['level'])

    for spell in cleric_spells:
        print(f'* {spell.oneline()}')
        text = spell.get('text', False)
        if text:
            print(indent(text, '  " '))

    for spell in cleric_spells:
        if 'gp' in spell['components']:
            print(f'{spell["name"]}: {spell["components"]}')
        #print(spell['components'])
        #if 'gp' in spell['components'].get('M', ''):
        #    print(f'{spell["name"]}: {spell["components"]["M"]}')

    mod_spells = ['Detect Thoughts', 'Detect Magic', 'See Invisibility']
    for spell in spells:
        if spell['name'] in mod_spells:
            print(f'* {spell.oneline()}')
            print(indent(spell['text'], '  " '))

def battle_royale_creatures():
    """Interesting creature options for battle royale at odd CRs.

    """
    blindsight = sorted(M.where(senses=p.key('blindsight'))
    truesight = sorted(M.where(senses=p.key('truesight')

    blindsight = sorted(((m.cr, m.name) for m in M.where(senses=p.key('blindsight'))), key=lambda t: t[0])

    pare = lambda mlist: [m for m in mlist if m.cr % 2 == 1 and m.cr > 1 and m.cr < 19]
    printms = lambda mlist: '\n'.join(f'* {int(m.cr)}: {m.name}' for m in mlist)
