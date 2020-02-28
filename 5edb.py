from lxml import etree
from itertools import groupby
from collections import defaultdict
import re
from pprint import pprint

debug = print

def group(iterable, key):
    ret = defaultdict(list)
    for i in iterable:
        ret[key(i)].append(i)
    return ret

def sort_group(group):
    return sorted(group.items(), key=lambda i: len(i[1]), reverse=True)

def parse_db(db_file='FC5eXML/CoreOnly.xml'):
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
    """I thiiiiink I don't need this
    def parse_subclass(c):
        m = re.match('^\s*(?P<class>[^(]]+)\s*'
                     + '(?P<subclass>\([^)]+\))?\s*$', c)
        m = m.groups()
        c = m[0]
        s = m[1][1:][:-1].trim().rtrim()
        return c, s
    """
    return sorted(classes)

def parse_spell_text(lines):
    state = {'source': None}
    def process(lines):
        for line in lines:
            if line is None:
                yield ''
            elif line[:8] == 'Source: ':
                if state['source']:
                    debug('Found two "Source: " lines')
                state['source'] = line[8:]
            else:
                yield line.strip()
    text = '\n'.join(process(lines))
    return text, state['source']

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
        spell['text'], spell['source'] = parse_spell_text(n.text for n in node.findall('text'))
        spell['roll'] = getattr(node.find('roll'), 'text', None)
        #TODO: figure out what to do with this property
        yield spell

def parsed_spells_analysis(spells):
    print('spell count: {0}'.format(len(spells)))
    print('first spell:')
    pprint(spells[0])

if __name__ == '__main__':
    tree = parse_db()
    #spell_tag_analysis(tree)
    parsed = list(parse_spells(tree))
    parsed_spells_analysis(parsed)
