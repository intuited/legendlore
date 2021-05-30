import re
from lxml import etree
from logging import debug, warning, error
from collections import namedtuple
from functools import reduce
from pprint import pprint, pformat
from textwrap import dedent
from fractions import Fraction
import dnd5edb
from dnd5edb import predicates, datatypes
from itertools import groupby, chain
chainfi = chain.from_iterable

default_db_file = 'FC5eXML/Collections/CoreOnly.xml'

def yield_args(*args):
    yield args

def anyfalse(bools):
    """Returns True iff any elements of iterable `bools` are False

    >>> anyfalse([True, True])
    False
    >>> anyfalse([True, False, True])
    True
    >>> anyfalse(None)
    False
    """
    if bools is None: return False
    for b in bools:
        if not b:
            return True
    return False

def dict_merge(d1, d2):
    """Merges dictionaries and returns the result."""
    d = {}
    d.update(d1)
    d.update(d2)
    return d


class XML:
    """Singleton class encapsulating the data read from the database file."""
    #TODO: make `tree` and `spells` properties if that's a thing I can do with a class
    #TODO: move the db filename in here
    tree = None
    spells = None

    @classmethod
    def apply_errata(cls, tree):
        """Corrects errors that have been discovered in the XML file."""
        #darkling = tree.xpath("//monster[name/text() = 'Darkling']")[0]
        #con = darkling.find('con')
        #con.text = '12'

    @classmethod
    def parse_db(cls, db_file=default_db_file):
        """Parse XML file with lxml parser."""
        debug('Parsing xml...')
        parser = etree.XMLParser()
        with open(db_file, 'r') as xmlfile:
            tree = etree.parse(xmlfile, parser)
        debug('...done')
        cls.apply_errata(tree)
        return tree

    @classmethod
    def get_tree(cls, db_file=default_db_file):
        """Returns a tree at the top level of the parsed DB.

        Parses it if it has not already been processed.
        """
        if not cls.tree:
            cls.tree = cls.parse_db(db_file)
        return cls.tree

# `Reference` tuple used by Spell class
Reference = namedtuple('Reference', ('book', 'page'))

class Spell():
    """Class functions to parse spell nodes."""

    @classmethod
    def parse(cls, node):
        """Parse a spell from a node in the tree."""
        spell = {}
        spell['name'] = node.find('name').text
        spell['level'] = int(node.find('level').text)
        #TODO: validation to confirm that this value is between 1 and 9
        spell['school'] = dnd5edb.Spell.schools[getattr(node.find('school'), 'text', None)]
        spell['ritual'] = True if getattr(node.find('ritual'), 'text', False) == "YES" else False
        spell['time'] = cls.parse_casting_time(node.find('time').text)
        spell['range'] = cls.parse_spell_range(node.find('range').text)
        spell['components'] = cls.parse_spell_components(node.find('components').text)
        spell['concentration'], spell['duration'] = cls.parse_spell_duration(node.find('duration').text)
        spell['classes'] = cls.parse_spell_classes(node.find('classes').text)
        spell['text'], spell['sources'] = cls.parse_spell_text(n.text for n in node.findall('text'))
        spell['roll'] = getattr(node.find('roll'), 'text', None)
        #TODO: figure out what to do with this property

        return spell

    casting_times = set()
    @classmethod
    def parse_casting_time(cls, time):
        #TODO: write this, validate
        # Why are there None values for this?
        try:
            return datatypes.CastingTime(time)
        except KeyError as e:
            warning(e)
            return time

    @classmethod
    def parse_spell_range(cls, r):
        try:
            return datatypes.SpellRange(r)
        except KeyError as e:
            warning(e)
            return r

    @classmethod
    def parse_spell_components(cls, text):
        """Returns a dictionary with form resembling

        {'V': True,
         'M': "a sprig of rosemary"}

        Initial strings are comma-separated strings of one of these forms:
        * V
        * S
        * M (...)

        >>> Spell.parse_spell_components('V, S, M (a sprinkling of holy water, rare incense, and powdered ruby worth at least 1,000 gp)')
        {'M': 'a sprinkling of holy water, rare incense, and powdered ruby worth at least 1,000 gp', 'S': True, 'V': True}
        """
        return text

        # Okay, this doesn't work because the parenthetical string after M
        # sometimes contains commas
        #if text is None:
        #    return {}
        #components = re.split(' ?, ?', text)
        #components = (c.strip() for c in components)
        #ret = {}
        #for c in components:
        #    if re.fullmatch('[vs]', c, re.I):
        #        ret[c.upper()] = True
        #    elif c[0] == 'M':
        #        try:
        #            specific = re.fullmatch('M(?: \(([^)]+)\))?', c).group(1)
        #            ret['M'] = specific if specific else True
        #        except AttributeError:
        #            warning(f'parse_spell_components: re match fail on material component "{c}" for text "{text}"')
        #            return {}
        #    else:
        #        warning(f'parse_spell_components: parse fail on text "{text}"')
        #        return {}

        #return ret

    @classmethod
    def parse_spell_duration(cls, duration):
        """Return: concentration, duration = ({True, False}, [STRING])"""
        if duration is None:
            return False, None

        if duration[:15] == 'Concentration, ':
            conc, time = True, duration[15:]
        elif duration[:15] == 'Instantaneous, ':
            conc, time = False, duration[15:]
        else:
            conc, time = False, duration

        try:
            return conc, datatypes.SpellDuration(time)
        except KeyError as e:
            warning(f'parse_spell_duration: unknown spell duration in "{duration}".  Parsed conc: {conc}, time: {time}')
            return conc, time

    @classmethod
    def parse_spell_classes(cls, classes):
        if classes is None:
            return []
        classes = re.split(',\s*', classes)
        classes = [c.strip() for c in classes]
        for c in classes:
            if c not in datatypes.caster_classes:
                warning(f'parse_spell_classes: unknown caster class "{c}"')
        return sorted(classes)

    valid_sources = [
        'Acquisitions Incorporated',
        "Elemental Evil Player's Companion",
        "Guildmasters' Guide to Ravnica",
        'Lost Laboratory of Kwalish',
        "Player's Handbook",
        'Princes of the Apocalypse',
        "Sword Coast Adventurer's Guide",
        "Volo's Guide to Monsters",
        "Xanathar's Guide to Everything",
        "Explorer's Guide to Wildemount",
        "Wayfinder's Guide to Eberron",
        "Eberron: Rising from the Last War",
        "Guildmasters' Guide to Ravnica",
        'Mythic Odysseys of Theros',
        "Icewind Dale: Rime of the Frostmaiden",
        "Tasha's Cauldron of Everything" ]

    @classmethod
    def parse_spell_source(cls, source):
        """Breaks source line into Reference(book, page) components.

        Returns a list of Reference objects.

        >>> source = "Xanathar's Guide to Everything, p. 152"
        >>> Spell.parse_spell_source(source)
        [Reference(book="Xanathar's Guide to Everything", page=152)]
        >>> Spell.parse_spell_source("")     # ignored because blank line
        []
        >>> source = "Xanathar's Guide to Everything p. 157, Elemental Evil Player's Companion p. 19, Wayfinder's Guide to Eberron p. 107, Eberron: Rising from the Last War p. 50"
        >>> Spell.parse_spell_source(source)
        [Reference(book="Xanathar's Guide to Everything", page=157), Reference(book="Elemental Evil Player's Companion", page=19), Reference(book="Wayfinder's Guide to Eberron", page=107), Reference(book='Eberron: Rising from the Last War', page=50)]
        >>> source = "Guildmasters' Guide to Ravnica"
        >>> Spell.parse_spell_source(source)
        [Reference(book="Guildmasters' Guide to Ravnica", page=None)]
        """
        source = source.strip()  # we're doing this more times than needed but nbd

        if source == "":
            # There are occasional blank lines, which we ignore
            return []

        m = re.match('^\s*(?P<book>.*?),?\s*p\.?\s*(?P<page>\d+)\s*(?P<extra>.*).*$', source)
        if m:
            book = m.groupdict()['book']
            if book not in cls.valid_sources:
                warning(f"parse_spell_source: invalid source '{book}' parsed on line '{source}'")
            this_reference = [Reference(m.groupdict()['book'], int(m.groupdict()['page']))]
            extra = m.groupdict()['extra']
        elif source in cls.valid_sources:  # some entries don't give page numbers
            this_reference = [Reference(source, None)]
            # Currently, pageless references only occur at the end of lines, so we can do this for now.
            extra = None
        else:
            warning(f"parse_spell_source: failed match on line '{source}'")
            return []
        #debug(book)

        if not extra:
            return this_reference
        if extra[0] == ',':
            return this_reference + cls.parse_spell_source(extra[1:].strip())
        else:
            warning(f"parse_spell_source: source '{source}': unknown extra '{extra}'")

    @staticmethod
    def expand_newlines(lines):
        r"""Split strings with newlines into multiple strings.

        >>> l = ["1\n2\n3", None, "4\n5\n6"]
        >>> list(Spell.expand_newlines(l))
        ['1', '2', '3', None, '4', '5', '6']
        """
        return chainfi([None] if l is None else l.split('\n') for l in lines)

    @classmethod
    def parse_spell_text(cls, lines):
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
        >>> parsed = Spell.parse_spell_text(text)
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
        >>> print(Spell.parse_spell_text(text)[1])
        (Reference(book="Player's Handbook", page=211),)

        >>> text = [
        ...     "Source: Xanathar's Guide to Everything p. 157, Elemental Evil Player's Companion p. 19", 
        ...     "Wayfinder's Guide to Eberron p. 107, Eberron: Rising from the Last War p. 50"]
        >>> print(Spell.parse_spell_text(text)[1])
        (Reference(book="Xanathar's Guide to Everything", page=157), Reference(book="Elemental Evil Player's Companion", page=19), Reference(book="Wayfinder's Guide to Eberron", page=107), Reference(book='Eberron: Rising from the Last War', page=50))
        """
        text_lines = []    # Accumulates lines of spell text in the for loop
        sources = []       # Accumulates Reference objects in the for loop
        in_sources = False # State that tracks if we're recording sources

        # Break out newlines in the list of strings
        lines = list(Spell.expand_newlines(lines))

        for line in lines:
            if line is None:
                if in_sources:
                    in_sources = False
                continue

            line = line.strip()
            if line[:8] == 'Source: ':
                in_sources = True
                sources += cls.parse_spell_source(line[8:])
            elif in_sources:
                sources += cls.parse_spell_source(line)
            else:
                text_lines.append(line)

        return '\n'.join(text_lines), tuple(sources)

#### Fundamental parsing functions
def yield_text(element, node):
    """The most basic element parser.

    Just returns (tag, text).
    """
    if element.text is None:
        debug(f'yield_text: None value for text in element with tag "{element.tag}"')
        # This can happen when there's a tag like `<spells/>` in the XML
        return
    else:
        yield (element.tag, element.text)

def yield_int(element, node):
    """Yield an integer that comprises the entirety of `element.text`."""
    if element.text is None:
        debug(f'yield_int: None value for text in element with tag "{element.tag}"')
    else:
        yield (element.tag, int(element.text))

def yield_fraction(element, node):
    """Convert fractional text field to float and yield (field, result)

    >>> from dnd5edb.test import obj_fromdict
    >>> fakenode = lambda v: obj_fromdict({'tag': 'cr', 'text': v})
    >>> test = lambda text: dict(yield_fraction(fakenode(text), None))
    >>> test(None)
    {}
    >>> test('42')
    {'cr': 42.0}
    >>> test('4/2')
    {'cr': 2.0}
    >>> test('2/4')
    {'cr': 0.5}
    >>> from unittest import TestCase
    >>> with TestCase.assertLogs(_) as cm:
    ...     print(test('not a fraction'))
    ...     print(cm.output)
    {}
    ['WARNING:root:yield_fraction: failed to parse text "not a fraction"']
    """
    field = element.tag
    text = element.text

    if text == None:
        debug(f'yield_fraction: None value for text in element with tag "{field}"')
        return

    try:
        yield (field, float(Fraction(text)))
    except ValueError:
        warning(f'yield_fraction: failed to parse text "{text}"')

#### Base parser class
class NodeParser():
    """Base class for objects which parse nodes."""

    @classmethod
    def parse(cls, node):
        """Returns iterable of (field, value) pairs.

        Iterates through elements of `node`, calling the appropriate
        `yield_` method for each element.

        `yield_` methods are generators which iterate (field, value) tuples.

        For example, yield_ac yields two or three such tuples:
        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'ac', 'text': v})
        >>> list(MonsterParser.yield_ac(fakenode('10 (natural armor)'), None))
        [('ac', '10 (natural armor)'), ('ac_num', 10), ('armor', 'natural armor')]
        >>> list(MonsterParser.yield_ac(fakenode('11'), None))
        [('ac', '11'), ('ac_num', 11)]

        Issues a warning if an element is encountered for which there is no handler.
        """
        for element in node:
            try:
                parsefn = getattr(cls, 'yield_' + element.tag)
            except AttributeError:
                warning(f'NodeParser.parse: unknown tag "{element.tag}"')
                continue
            try:
                yield from parsefn(element, node)
            except TypeError as e:
                warning(f'NodeParser.parse: TypeError "{e}" while parsing element "{element}" in node "{node}"')

    yield_name = staticmethod(yield_text)

# Derived parser classes
class MonsterParser(NodeParser):
    """Parser for <monster> nodes."""
    yield_size = yield_text
    yield_type = yield_text
    yield_alignment = yield_text

    @staticmethod
    def yield_ac(element, node):
        """Yield ac attributes.

        If a numeric AC is parsed, it is yielded as `ac_num`.
        If information on armor is parsed in the parentheses following the AC,
        it is yielded as `armor`.
        In any case, the full text of the field is yielded as `ac`.
        """
        text = element.text

        yield ('ac', text)

        #m = re.match('^(\d+)(?: \(.*)?$', text)
        m = re.match('^(\d+)(?: \(([^)]*)\))?$', text)
        if m is None:
            debug(f'Failed match for AC text "{text}"')
            return
        g = m.groups()
        if g[0]:
            yield ('ac_num', int(g[0]))
        if g[1]:
            yield ('armor', g[1])

    @staticmethod
    def yield_hp(element, node):
        """Assign to hp attributes.

        Similar to yield_ac but parses `hp` and `hitdice` attributes.

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'hp', 'text': v})
        >>> d = dict(MonsterParser.yield_hp(fakenode('135 (18d10+36)'), None))
        >>> d['hp']
        135
        >>> d['hitdice']
        '18d10+36'
        >>> d = dict(MonsterParser.yield_hp(fakenode('0'), None))
        >>> d['hp']
        0
        >>> d['hitdice']
        Traceback (most recent call last):
            ...
        KeyError: 'hitdice'
        """
        text = element.text

        m = re.match('^(\d+)(?: \(([^)]*)\))?$', text)
        if m is None:
            debug(f'Failed match for HP text "{text}"')
            return
        g = m.groups()
        yield ('hp', int(g[0]))
        if g[1]:
            yield ('hitdice', g[1])

    @staticmethod
    def yield_speed(element, node):
        """Parse speed fields into a dictionary.

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'speed', 'text': v})
        >>> test = lambda t: dict(MonsterParser.yield_speed(fakenode(t), None))['speed']
        >>> test('25 ft.')
        {'walk': 25}
        >>> result = test('40 ft., fly 80 ft., swim 40 ft.')
        >>> result == {'walk': 40, 'fly': 80, 'swim': 40}
        True
        >>> result = test('40 ft., burrow 30 ft., fly 80 ft., swim 40 ft.')
        >>> result == {'walk': 40, 'burrow': 30, 'fly': 80, 'swim': 40}
        True
        >>> result = test('30 ft., climb 30 ft.')
        >>> result == {'walk': 30, 'climb': 30}
        True
        >>> result = test('swim 50 ft.')
        >>> result == {'swim': 50}
        True
        >>> result = test('60 ft. (30 ft.in goblin form)')
        >>> result == {'walk': 60, 'walk (in goblin form)': 30}
        True
        >>> result = test('30 ft. (20 ft. and swim 40 ft. in hybrid form)')
        >>> result == {'walk': 30, 'walk (in hybrid form)': 20,
        ...                        'swim (in hybrid form)': 40}
        True
        >>> result = test('60 ft., fly 120 ft. (hover)')
        >>> result == {'walk': 60, 'fly': 120}
        True
        >>> result = test('30 ft. (60 ft. with boots of speed)')
        >>> result == {'walk': 30, 'walk (with boots of speed)': 60}
        True
        >>> result = test('15 ft. (30 ft. when rolling, 60 ft. rolling downhill)')
        >>> result == {'walk': 15, 'walk (when rolling)': 30,
        ...                        'walk (when rolling downhill)': 60}
        True
        >>> result = test('30 ft. (climb 30 ft., fly 60 ft., in bat or hybrid form)')
        >>> result == {'walk': 30, 'climb (in bat or hybrid form)': 30,
        ...                        'fly (in bat or hybrid form)': 60}
        True
        >>> result = test('50 ft. (in one direction chosen at the start of its turn)')
        >>> result == {'walk (in one direction chosen at the start of its turn)': 50}
        True
        >>> result = test('30 ft., fly 50 ft. in raven and hybrid forms')
        >>> result == {'walk': 30, 'fly (in raven and hybrid forms)': 50}
        True
        >>> result = test('walk 40 ft., climb 30 ft., fly 40 ft.')
        >>> result == {'walk': 40, 'climb': 30, 'fly': 40}
        True
        >>> result = test('30 ft. swim')
        >>> result == {'swim': 30}
        True
        >>> result = test('30 ft., 30 ft. swim')
        >>> result == {'walk': 30, 'swim': 30}
        True
        >>> test("12 miles per hour (288 miles per day)")
        {'mph': 12}
        """
        text = element.text

        movement_types = ['walk', 'fly', 'swim', 'climb', 'burrow']
        mt_re = '(?:' + '|'.join(movement_types) + ')'
        vector_re_basic = f'(?:{mt_re} )?\d+ ?ft\.?' # [movement_type] speed
        vector_re_hover = f'fly \d+ ft. \([Hh]over\)'
        vector_re_speed_first = f'\d+ ?ft\.? {mt_re}'
        vector_just_a_number = f'\d+'
        vector_vehicle_speed = r'^\d+ miles per hour \(\d+ miles per day\)$'
        vector_re = (f'(?:{vector_re_basic}|{vector_re_hover}|'
                      + f'{vector_re_speed_first}|{vector_just_a_number}|'
                      + f'{vector_vehicle_speed})')

        csv_match_re = f'^({vector_re})(?:, ({vector_re}))*$' # list of speeds, no ()

        def parse_vector(vector):
            """Parse a movement vector and return (type, speed).

            Used by Monster._assign_speed().
            
            >>> parse_vector('60 ft.')
            ('walk', 60)
            >>> parse_vector('climb 30 ft.')
            ('climb', 30)
            >>> parse_vector('yeet 10000 ft.')
            These doctests don't run because parse_vector is an internal function
            >>> parse_vector('fly 30 ft. (hover)')
            ('fly', 30)
            >>> parse_vector("12 miles per hour (288 miles per day)")
            ('mph', 12)
            """
            # capture groups for type and speed
            parse_re = f'^(?:({mt_re}) )?(\d+) ?ft\.?(?: \([Hh]over\))?$'
            parse_re_speed_first = f'^(\d+) ?ft\.? ({mt_re})$'
            parse_re_just_a_number = '^(\d+)$'
            parse_re_vehicle_speed = '^(\d+) miles per hour \(\d+ miles per day\)$'

            m = re.match(parse_re, vector)
            if m:
                g = m.groups()
                if g[0] is None:  # the movement type was implied
                    mtype = 'walk'
                else:
                    mtype = g[0]
                return (mtype, int(g[1]))

            m = re.match(parse_re_speed_first, vector)
            if m:
                return (m.group(2), int(m.group(1)))

            m = re.match(parse_re_just_a_number, vector)
            if m:
                return ('walk', int(m.group(1)))

            m = re.match(parse_re_vehicle_speed, vector)
            if m:
                return ('mph', int(m.group(1)))

            raise Exception(f'parse_vector: invalid match on "{vector}"')

        if re.match(csv_match_re, text):
            csv_iter_re = f'^({vector_re})(?:, ({vector_re}(?:, {vector_re})*))?$'
            def iter_vectors(text):
                while text:
                    m = re.match(csv_iter_re, text)
                    if m:
                        yield m.group(1)
                        text = m.group(2)
                    else:
                        raise Exception(f'iter_vectors failed to match text "{text}"')
            yield('speed', dict(parse_vector(v) for v in iter_vectors(text)))
        else:
            # manually handle a bunch of special cases
            irregulars = {
                "60 ft. (30 ft.in goblin form)":
                    {'walk': 60, 'walk (in goblin form)': 30},
                "30 ft. (20 ft. and swim 40 ft. in hybrid form)":
                    {'walk': 30, 'walk (in hybrid form)': 20,
                                 'swim (in hybrid form)': 40},
                "60 ft., fly 120 ft. (hover)":
                    {'walk': 60, 'fly': 120},
                "30 ft. (60 ft. with boots of speed)":
                    {'walk': 30, 'walk (with boots of speed)': 60},
                "15 ft. (30 ft. when rolling, 60 ft. rolling downhill)":
                    {'walk': 15, 'walk (when rolling)': 30,
                                 'walk (when rolling downhill)': 60},
                "30 ft. (climb 30 ft., fly 60 ft., in bat or hybrid form)":
                    {'walk': 30, 'climb (in bat or hybrid form)': 30,
                                 'fly (in bat or hybrid form)': 60},
                "50 ft. (in one direction chosen at the start of its turn)":
                    {'walk (in one direction chosen at the start of its turn)':
                     50},
                "30 ft., fly 50 ft. in raven and hybrid forms":
                    {'walk': 30, 'fly (in raven and hybrid forms)': 50},
                "30 ft. (40 ft., climb 30 ft. in bear or hybrid form)":
                    {'walk': 30, 'climb (in bear or hybrid form)': 30},
                "30 ft. (40 ft. in boar form)":
                    {'walk': 30, 'walk (in boar form)': 40},
                "30 ft. (40 ft. in tiger form)":
                    {'walk': 30, 'walk (in tiger form)': 40},
                "30 ft. (40 ft. in wolf form)":
                    {'walk': 30, 'walk (in wolf form)': 40},
                "50 ft,":
                    {'walk': 50} }

            try:
                yield ('speed', irregulars[text])
            except KeyError:
                warning(f'yield_speed failed to match "{text}"')

    (yield_str, yield_dex, yield_con,
     yield_int, yield_wis, yield_cha) = map(staticmethod, [yield_int] * 6)

    @staticmethod
    def yield_saves(element, node):
        """Yield ('saves', {..})

        Dictionary entries are a stat (eg 'str') and an integer.

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'saves', 'text': v})
        >>> test = lambda text: next(MonsterParser.yield_saves(fakenode(text), None))
        >>> test(None)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> test('Dex +5, Con +11, Wis +7, Cha +9')
        ('saves', {'dex': 5, 'con': 11, 'wis': 7, 'cha': 9})
        """
        text = element.text

        if text is None:
            return

        try:
            saves = re.split(', ', text)
            saves = (re.split(' +', save) for save in saves)
            saves = ((stat.lower(), int(val)) for stat, val in saves)
        except:
            error(f'yield_saves: parsing error for text "{text}"')
            return

        yield ('saves', dict(saves))

    @staticmethod
    def yield_skill(element, node):
        """Yield ('skills', {..})

        Dictionary entries are a skill (eg 'Athletics') and an integer.

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'skill', 'text': v})
        >>> test = lambda text: next(MonsterParser.yield_skill(fakenode(text), None))
        >>> test(None)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> test('Perception +5')
        ('skills', {'Perception': 5})
        >>> test('History +7, Perception +11, Persuasion +8, Stealth +5')
        ('skills', {'History': 7, 'Perception': 11, 'Persuasion': 8, 'Stealth': 5})
        """
        text = element.text

        if text is None:
            return

        all_skills = [
            'Athletics', 'Acrobatics', 'Sleight of Hand', 'Stealth', 'Arcana',
            'History', 'Investigation', 'Nature', 'Religion', 'Animal Handling',
            'Insight', 'Medicine', 'Perception', 'Survival', 'Deception',
            'Intimidation', 'Performance', 'Persuasion' ]

        def normalize(skill):
            for s in all_skills:
                if skill.lower() == s.lower():
                    return s
            raise Exception(f'Unknown skill "{skill}"')

        try:
            skills = re.split(', ?', text)
            skills = (re.split(' \+', skill) for skill in skills)
            skills = dict((normalize(skill), int(val)) for skill, val in skills)
        except Exception as e:
            error(f'yield_skill: {type(e)} "{e}" for text "{text}"')

        yield ('skills', skills)

    @staticmethod
    def yield_damage_types(element, node):
        """Yields the `field` and the damage types that apply to it for `text`.

        `field` can be "resist", "vulnerable", or "immune"

        Yield format e.g. ('resist': {..})

        May also yield notes in the form ('resist_notes': {..})

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'resist', 'text': v})
        >>> test = lambda text: list(MonsterParser.yield_damage_types(fakenode(text), None))
        >>> test(None)
        []
        >>> pprint(test('lightning; thunder; bludgeoning, piercing, ' + 
        ...             'and slashing from nonmagical attacks'))
        [('resist',
          {'lightning',
           'nonmagical bludgeoning',
           'nonmagical piercing',
           'nonmagical slashing',
           'thunder'})]
        >>> pprint(test('damage from spells; non magical bludgeoning, ' + 
        ...             'piercing, and slashing (from stoneskin)'))
        [('resist',
          {'damage from spells',
           'nonmagical bludgeoning',
           'nonmagical piercing',
           'nonmagical slashing'}),
         ('resist_notes',
          {'from stoneskin': ['nonmagical bludgeoning',
                              'nonmagical piercing',
                              'nonmagical slashing']})]
        >>> r = test('acid, cold, fire, lightning, thunder')
        >>> r == [('resist', {'acid', 'cold', 'fire', 'lightning', 'thunder'})]
        True
        >>> pprint(test('While wearing the mask of the Dragon Queen: acid, cold, ' +
        ...             'lightning, poison; bludgeoning, piercing, ' +
        ...             'and slashing damage from nonmagical weapons'))
        [('resist',
          {'acid',
           'cold',
           'lightning',
           'nonmagical bludgeoning',
           'nonmagical piercing',
           'nonmagical slashing',
           'poison'}),
         ('resist_notes',
          {'While wearing the mask of the Dragon Queen': ['acid',
                                                          'cold',
                                                          'lightning',
                                                          'poison']})]
        """
        field = element.tag
        text = element.text

        if text == None:
            return

        found, notfound = [], []

        # First, parse the text, first along semicolon delimeters,
        # then along commas
        scsvs = re.split('; ?', text.lower()) #Semi-Colon-Separated Values
        scsvs = map(str.strip, scsvs)

        damage_types = set()
        damage_types.update(datatypes.damage_types)
        damage_types.update(datatypes.damage_mappings.keys())

        for scsv in scsvs:
            if scsv in damage_types:
                found.append(scsv)
            else:  # check if all subitems from comma-split match
                csvs = re.split(', ?', scsv) #Comma-Separated Values
                csvs = list(map(str.strip, csvs))
                if anyfalse(csv in damage_types for csv in csvs):
                    notfound.append(scsv)
                else:
                    found += csvs

        for item in notfound:
            warning(f'Unrecognised scsv "{item}" in text "{text}"')

        # Now check the parsed field contents for any items
        # which require remapping to multiple or different items
        # and/or have associated notes.
        field_contents = []
        field_notes = {}
        for i in found:
            if i in datatypes.damage_mappings.keys():
                try:
                    field_contents += datatypes.damage_mappings[i]['types']
                    field_notes.update(datatypes.damage_mappings[i]['notes'])
                except KeyError:
                    None
            else:
                field_contents.append(i)

        if field_contents:
            yield (field, set(field_contents))
        if field_notes:
            yield (f'{field}_notes', field_notes)
    yield_resist = yield_damage_types
    yield_vulnerable = yield_damage_types
    yield_immune = yield_damage_types

    @staticmethod
    def yield_conditionImmune(element, node):
        """Parse field containing a set of conditions and yield the result.

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'conditionImmune', 'text': v})
        >>> test = lambda text: dict(MonsterParser.yield_conditionImmune(fakenode(text), None))
        >>> ptest = lambda text: pprint(test(text), width=200)
        >>> test(None)
        {}
        >>> r = test('charmed, frightened, paralyzed, petrified, poisoned , unconscious')
        >>> r == {'conditionImmune': {'charmed', 'frightened', 'unconscious', 'poisoned', 'paralysed', 'petrified'}}
        True
        >>> test('petrified')
        {'conditionImmune': {'petrified'}}
        >>> r = test('While wearing the mask of the Dragon Queen: charmed, frightened, poisoned')
        >>> r['conditionImmune'] == {'charmed', 'frightened', 'poisoned'}
        True
        >>> pprint(r['conditionImmune_notes'])
        {'charmed': 'While wearing the mask of the Dragon Queen',
         'frightened': 'While wearing the mask of the Dragon Queen',
         'poisoned': 'While wearing the mask of the Dragon Queen'}
        >>> test('Frightened')
        {'conditionImmune': {'frightened'}}
        """
        field = element.tag
        text = element.text

        full_text = { # special cases
            'While wearing the mask of the Dragon Queen: charmed, frightened, poisoned': {
                field: {'charmed', 'frightened', 'poisoned'},
                f'{field}_notes': {
                    'charmed': 'While wearing the mask of the Dragon Queen',
                    'frightened': 'While wearing the mask of the Dragon Queen',
                    'poisoned': 'While wearing the mask of the Dragon Queen'}},
        }
        conditions = { # format: {RE: normalized representation}
            'blinded': None,
            'charmed': None,
            'deafened': None,
            'exhaustion': None,
            'frightened': None,
            'grappled': None,
            'incapacitated': None,
            'paraly[sz]ed': 'paralysed',
            'petrified': None,
            'poisoned': None,
            'prone': None,
            'restrained': None,
            'stunned': None,
            'uncons?cious': 'unconscious',
        }

        if text == None:
            return

        for ft, v in full_text.items():
            if re.fullmatch(ft, text):
                yield from v.items()
                return

        found = []
        notfound = []
        csvs = re.split(' ?, ?', text)
        def process_csv(csv):
            for c, v in conditions.items():
                if re.fullmatch(c, csv, re.I):
                    return v if v else c
            raise Exception(f'MonsterParser.yield_conditionImmune: Unmatched CSV "{csv}" in text "{text}" of element "{element}" in node "{node}"')

        try:
            yield (field, set(process_csv(csv) for csv in csvs))
        except Exception as e:
            warning(f'yield_condition: {e.args[0]}')

    @staticmethod
    def yield_senses(element, node):
        """Parse 'senses' fields and yield the results.

        >>> from dnd5edb.test import obj_fromdict
        >>> fakenode = lambda v: obj_fromdict({'tag': 'senses', 'text': v})
        >>> test = lambda text: dict(MonsterParser.yield_senses(fakenode(text), None))
        >>> test(None)
        {}
        >>> next(MonsterParser.yield_senses(fakenode(None), None))
        Traceback (most recent call last):
            ...
        StopIteration
        >>> test('darkvision 120 ft.')
        {'senses': {'darkvision': 120}}
        >>> test('blindsight 30 ft., darkvision 60 ft.')
        {'senses': {'blindsight': 30, 'darkvision': 60}}
        >>> pprint(test('darkvision 60 ft. (rat form only)'))
        {'senses': {'darkvision': 60}, 'senses_notes': {'darkvision': 'rat form only'}}
        """
        field = element.tag
        text = element.text

        just_senses_res = { # match component of text, map to fn(groups) of match
            'darkvision (\d+) ?(?:ft\.?)?': lambda *a: {'darkvision': int(a[0])},
            'blindsight (\d+) ?ft\.?':      lambda *a: {'blindsight': int(a[0])},
            'truesight (\d+) ?ft\.?':       lambda *a: {'truesight': int(a[0])},
            'tremorsense (\d+) ?ft\.?':     lambda *a: {'tremorsense': int(a[0])},
            'blindsight (\d+) ?ft\.? \(blind beyond this (?:radius|distance)\)':
                lambda *a: {'blindsight': int(a[0])},
            'blindsight (\d+) ?ft. or (\d+) ?ft. while deafened \(blind beyond this radius\)':
                lambda *a: {'blindsight': int(a[0]), 'blindsight while deafened': int(a[1])},
            'darkvision (\d+) ?ft\. \((?:including|penetrates) magical darkness\)':
                lambda *a: {'devilsight': int(a[0])},
            "darkvision (\d+) ?ft\. \(see devil's sight below\)":
                lambda *a: {'devilsight': int(a[0])},
        }
        with_notes_strings = { # match full text, map to full dictionary
            'darkvision 60 ft. (rat form only)':
                {'senses': {'darkvision': 60},
                 'senses_notes': {'darkvision': 'rat form only'}},
            'While wearing the Mask of the Dragon Queen: darkvision 60 ft.':
                {'senses': {'darkvision': 60},
                 'senses_notes': 'darkvision while wearing the Mask of the Dragon Queen'},
            'darkvision 60 ft. (can see invisible creatures out to the same range)':
                {'senses': {'darkvision': 60},
                 'senses_notes': {'darkvision': 'can see invisible creatures to same range'}},
            'blindsight 120 ft. (blind beyond this radius); see also "detect sentience" below':
                {'senses': {'blindsight': 120},
                 'senses_notes': {'blindsight': 'blind beyond this radius'}},
            'darkvision 60ft. (beast form only)':
                {'senses': {'darkvision': 60},
                 'senses_notes': {'darkvision': 'beast form only'}},
        }

        def map_component(c):
            """Find a matching RE and map the component to a dictionary.

            >>> map_component('darkvision 120 ft')
            {'darkvision': 120}
            """
            for r, f in just_senses_res.items():
                m = re.fullmatch(r, c, re.I)
                if m:
                    return f(*m.groups())

        if text is None:
            return

        for s, v in with_notes_strings.items():
            if s == text:
                yield from v.items()
                return

        components = re.split(', ?', text)
        mapped_components = (map_component(c) for c in components)
        mapped_components = (m for m in mapped_components if m) # drop Nones
        try:
            senses = reduce(dict_merge, mapped_components)
        except TypeError:
            warning(f'yield_senses: failed match on text "{text}"')
            return

        yield (field, senses)

    yield_passive = yield_int
    yield_description = yield_text
    yield_cr = yield_fraction
    yield_spells = yield_text
    yield_slots = yield_text

    ## TODO: write these stubs
    @staticmethod
    def yield_action(element, node):
        debug(f'MonsterParser.yield_action called for element "{element}"')
        if False:
            yield

    @staticmethod
    def yield_save(element, node):
        debug(f'MonsterParser.yield_save called for element "{element}"')
        if False:
            yield

    @staticmethod
    def yield_languages(element, node):
        debug(f'MonsterParser.yield_languages called for element "{element}"')
        if False:
            yield

    @staticmethod
    def yield_trait(element, node):
        debug(f'MonsterParser.yield_trait called for element "{element}"')
        if False:
            yield

    @staticmethod
    def yield_environment(element, node):
        debug(f'MonsterParser.yield_environment called for element "{element}"')
        if False:
            yield

    @staticmethod
    def yield_legendary(element, node):
        debug(f'MonsterParser.yield_legendary called for element "{element}"')
        if False:
            yield

    @staticmethod
    def yield_reaction(element, node):
        debug(f'MonsterParser.yield_reaction called for element "{element}"')
        if False:
            yield
