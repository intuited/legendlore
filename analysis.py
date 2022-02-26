"""analysis.py

Various functions that use the module code to analyse the database.
Not part of the core functionality, and largely vestigial at this point.
"""
from legendlore.collection import Monsters, Spells
from collections import defaultdict, Counter
from pprint import pprint, pformat
from functools import partial
import statistics
from legendlore.parse import XML

pprint = partial(pprint, indent=2, width=100)
pformat = partial(pformat, indent=2, width=100)

def indent(text, prefix='    '):
    return '\n'.join(prefix + line for line in text.split("\n"))

def group(iterable, key):
    ret = defaultdict(list)
    for i in iterable:
        ret[key(i)].append(i)
    return ret

def sort_group(group):
    return sorted(group.items(), key=lambda i: len(i[1]), reverse=True)

# TODO: update so it can take zero arguments
def spell_tag_analysis(tree=XML.get_tree()):
    spells = tree.xpath("//spell")
    spell_nodes = tree.xpath("//spell/*")
    print(len(spells))
    print(len(spell_nodes))
    print(dir(spell_nodes[0]))
    print(spell_nodes[0].__class__)
    print(spell_nodes[0].tag)

    spell_tags = set((node.tag for node in spell_nodes))
    print(spell_tags)

    spell_tag_groups = group(spell_nodes, lambda n: n.tag).items()
    for k, g in spell_tag_groups:
        print("{0}: {1} nodes".format(k, len(g)))
        value_group = group(g, lambda n: n.text)
        if len(value_group.keys()) > 20:
            print("  {0} unique values.  Top Ten:".format(len(value_group.keys())))
            topten = sort_group(value_group)[:10]
            summary = lambda i: '    {0}: {1}'.format(len(i[1]), str(i[0]))
            print('\n'.join(summary(item) for item in topten))
        else:
            for h, i in sort_group(value_group):
                print("  {0}: {1} nodes".format(h, len(i)))

# TODO: update so it can take zero arguments
def parsed_spells_analysis(spells):
    pprint = partial(pprint, indent=4)
    print('spell count: {0}'.format(len(spells)))
    print('first spell:')
    pprint(spells[0])
    print('class occurrence counts:')
    pprint(Counter(c for spell in spells for c in spell['classes']),
           compact=True, width=160)
    print('spells with no classes:')
    pprint([spell for spell in spells if not spell['classes']])
    print('spells with no source:')
    pprint([spell for spell in spells if not spell.get('sources', False)])
    print('spell books:')
    pprint(Counter(ref.book for s in spells for ref in s['sources']))

def analyze_monster_nodes(tree=XML.get_tree()):
    """Output a bunch of info about the monster nodes in the DB."""
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

def analyze_fey(tree=XML.get_tree()):
    """Breakdown of Fey monsters in 5e."""
    fey = [m for m in Monsters() if m.type.startswith('fey')]
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

def knowledge_cleric_spells(tree=XML.get_tree()):
    """Prints one-line summaries of knowledge cleric spells."""
    spells = Spells()

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
    M = Monsters()
    blindsight = sorted(M.where(senses=p.key('blindsight')))
    truesight = sorted(M.where(senses=p.key('truesight')))

    blindsight = sorted(((m.cr, m.name) for m in M.where(senses=p.key('blindsight'))), key=lambda t: t[0])

    pare = lambda mlist: [m for m in mlist if m.cr % 2 == 1 and m.cr > 1 and m.cr < 19]
    printms = lambda mlist: '\n'.join(f'* {int(m.cr)}: {m.name}' for m in mlist)

# Some utility functions that may be useful in the future
def print_spell_list(spells):
    """Prints formatted spell info for each spell in the list.

    Format:
        * SpellName Summary
          " Spell Text Line 1
          " Spell Text Line 2
          " ...

    The "SpellName Summary" line is the output of Spell.oneline().

    >>> print_spell_list(Spells().where(name='Compulsion'))
    * Compulsion A/30'/C<=1m (4:B)
      " Creatures of your choice that you can see within range and that can hear you must make a Wisdom saving throw. A target automatically succeeds on this saving throw if it can't be charmed. On a failed save, a target is affected by this spell. Until the spell ends, you can use a bonus action on each of your turns to designate a direction that is horizontal to you. Each affected target must use as much of its movement as possible to move in that direction on its next turn. It can take its action before it moves. After moving in this way, it can make another Wisdom saving throw to try to end the effect.
      " A target isn't compelled to move into an obviously deadly hazard, such as a fire pit, but it will provoke opportunity attacks to move in the designated direction.
    """
    print(spells.fmt(method='xlist'))
