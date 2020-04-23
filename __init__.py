from lxml import etree
from itertools import groupby, chain
chainfi = chain.from_iterable
from collections import defaultdict, Counter
import re
from pprint import pprint
from textwrap import dedent
from collections import namedtuple
from functools import partial

debug = print
log = print

pprint = partial(pprint, indent=4)

Reference = namedtuple('Reference', ('book', 'page'))

def group(iterable, key):
    ret = defaultdict(list)
    for i in iterable:
        ret[key(i)].append(i)
    return ret

def sort_group(group):
    return sorted(group.items(), key=lambda i: len(i[1]), reverse=True)

def parse_db(db_file='FC5eXML/CoreOnly.xml'):
    """Parse XML file with lxml parser."""
    debug('Parsing xml...')
    parser = etree.XMLParser()
    with open(db_file, 'r') as xmlfile:
        tree = etree.parse(xmlfile, parser)
    debug('...done')
    return tree

def spell_tag_analysis(tree):
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

def parse_casting_time(time):
    #TODO: write this, validate
    # Why are there None values for this?
    return time

def parse_spell_range(r):
    #TODO: write this, validate
    return r

def parse_spell_components(components):
    """Returns a dictionary with form resembling

    {'V': True,
     'S': False,
     'M': "a sprig of rosemary"}

    Initial strings are comma-separated strings of one of these forms:
    * V
    * S
    * M (...)
    """
    if components is None:
        return []
    c = []
    m = re.match('^[^(,]*,?', components.strip())
    while m:
        c.append(m.group().strip(' ,'))
        components = components[m.end():]
        m = re.match('^[^(,]*,', components.strip())
    return c

    """ uhhhh
    ret = {}
    m = re.match('^\s*(V|S|M\s*\([^)]*\)(,\s*)*)+\s*$')

    for c in components:
        if c[0] == 'V':
            ret['V'] = True
            assert len(c) == 1
        elif c[0] == 'S'
            ret['S'] = True
            assert len(c) == 1
        elif c[0] == 'M'
    """
    #TODO: finish this
    return components

def parse_spell_duration(duration):
    """Return: concentration, duration = ({True, False}, [STRING])"""
    #TODO: add validation
    if duration is None:
        return False, None

    if duration[:15] == 'Concentration, ':
        return True, duration[15:]
    else:
        return False, duration

def parse_spell_classes(classes):
    if classes is None:
        return []
    classes = re.split(',\s*', classes)
    classes = [c.strip() for c in classes]
    return sorted(classes)

def parse_spell_source(source):
    """Breaks source line into Reference(book, page) components.

    >>> source = "Xanathar's Guide to Everything, p. 152"
    >>> parse_spell_source(source)
    Reference(book="Xanathar's Guide to Everything", page=152)
    >>> source = "Player's Handbook, p. 277 (spell)"
    >>> parse_spell_source(source)
    Reference(book="Player's Handbook", page=277)
    >>> source = "Xanathar's Guide to Everything, p. 20 (class feature)"
    >>> parse_spell_source(source)
    """
    m = re.match('^(?P<book>.*?),?\s*p\.?\s*(?P<page>\d+)\s*(?P<extra>.*).*$', source)
    if m is None:
        log(f"parse_spell_source: failed match on line '{source}'")
        return None
    #debug(book)
    extra = m.groupdict()['extra']
    if extra == '(spell)' or not extra:
        return Reference(m.groupdict()['book'], int(m.groupdict()['page']))
    if extra == '(class feature)':
        return None
    else:
        log(f"parse_spell_source: unknown extra '{extra}'")

def expand_newlines(lines):
    r"""Split strings with newlines into multiple strings.

    >>> l = ["1\n2\n3", None, "4\n5\n6"]
    >>> list(expand_newlines(l))
    ['1', '2', '3', None, '4', '5', '6']
    """
    return chainfi([None] if l is None else l.split('\n') for l in lines)
    #for line in lines:
    #    if line is None:
    #        yield line
    #    else:
    #        for l in line.rstrip().split('\n'):
    #            yield l

def parse_spell_text(lines):
    """Parses list of strings containing <text> nodes from xml.

    Checks for source book in last line of `lines`.
    Returns (text, sources) where
    -   `text` is the newline-joined contents of non-source lines
    -   `sources` is a list of Reference namedtuples

    >>> text = [
    ...     "• A prone creature's only movement option is to crawl, unless it stands up and thereby ends the condition.",
    ...     "",
    ...     "• The creature has disadvantage on attack rolls.",
    ...     "",
    ...     "• An attack roll against the creature has advantage if the attacker is within 5 feet of the creature. Otherwise, the attack roll has disadvantage.",
    ...     None,
    ...     "Source: Xanathar's Guide to Everything, p. 168",
    ...     "Elemental Evil Player's Companion, p. 22",
    ...     "Princes of the Apocalypse, p. 240"]
    >>> parsed = parse_spell_text(text)
    >>> print(parsed[0])
    • A prone creature's only movement option is to crawl, unless it stands up and thereby ends the condition.
    <BLANKLINE>
    • The creature has disadvantage on attack rolls.
    <BLANKLINE>
    • An attack roll against the creature has advantage if the attacker is within 5 feet of the creature. Otherwise, the attack roll has disadvantage.
    >>> parsed[1] == (Reference("Xanathar's Guide to Everything", 168),
    ...               Reference("Elemental Evil Player's Companion", 22),
    ...               Reference("Princes of the Apocalypse", 240))
    True
    >>> text = [
    ...     "Your spell bolsters your allies with toughness and resolve. Choose up to three creatures within range. Each target's hit point maximum and current hit points increase by 5 for the duration.",
    ...     ""
    ...     "At Higher Levels: When you cast this spell using a spell slot of 3rd level or higher, a target's hit points increase by an additional 5 for each slot level above 2nd.",
    ...     None,
    ...     "Source: Player's Handbook, p. 211",
    ...     None,
    ...     "* Oath, Domain, or Circle of the Land spell (always prepared)"]
    >>> print(parse_spell_text(text)[1])
    (Reference(book="Player's Handbook", page=211),)
    """
    sources = []
    def process(lines):
        in_sources = False # State that tracks if we're recording sources
        lines = list(expand_newlines(lines))

        for line in lines:
            if line is None:
                if in_sources:
                    in_sources = False
                continue

            line = line.strip()
            if line[:8] == 'Source: ':
                in_sources = True
                parsed = parse_spell_source(line[8:])
            elif in_sources:
                parsed = parse_spell_source(line)
            else:
                yield line
                continue
            if parsed is not None:
                sources.append(parsed)
    text = '\n'.join(process(lines))
    return text, tuple(sources)

"""thing to parse the initial db.

okay so it needs to verify that it's correctly parsed things
by generating a 
"""

def parse_spells(tree):
    spells = tree.xpath("//spell")
    schools = {'EV': "Evocation",
               'T': "Transmutation",
               'C': "Conjuration",
               'A': "Abjuration",
               'EN': "Enchantment",
               'D': "Divination",
               'N': "Necromancy",
               'I': "Illusion",
               None: None}
    for node in spells:
        spell = {}
        spell['name'] = node.find('name').text
        spell['level'] = int(node.find('level').text)
        #TODO: validation to confirm that this value is between 1 and 9
        spell['school'] = schools[getattr(node.find('school'), 'text', None)]
        spell['ritual'] = True if node.find('ritual') == "YES" else False
        spell['time'] = parse_casting_time(node.find('time').text)
        spell['range'] = parse_spell_range(node.find('range').text)
        spell['components'] = parse_spell_components(node.find('components').text)
        spell['concentration'], spell['duration'] = parse_spell_duration(node.find('duration').text)
        spell['classes'] = parse_spell_classes(node.find('classes').text)
        spell['text'], spell['sources'] = parse_spell_text(n.text for n in node.findall('text'))
        spell['roll'] = getattr(node.find('roll'), 'text', None)
        #TODO: figure out what to do with this property
        yield spell

def parsed_spells_analysis(spells):
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
