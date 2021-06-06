import re
from lxml import etree
from logging import debug, warning, error
from functools import reduce, partial
from pprint import pprint, pformat
from textwrap import dedent
from fractions import Fraction
import dnd5edb
from dnd5edb import predicates, datatypes
from dnd5edb.datatypes import Reference
from itertools import groupby, chain
chainfi = chain.from_iterable
from collections import defaultdict

default_db_file = 'FC5eXML/Collections/CoreOnly.xml'

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

#### Generic parsing functions
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

def yield_datatype(datatype, element, node):
    """Instantiates an object of type `datatype` and yields it."""
    try:
        yield (element.tag, datatype(element.text))
    except KeyError as e:
        warning(e)
        yield (element.tag, element.text)

#### Base parser class
class NodeParser():
    """Base class for objects which parse nodes.

    Subclasses should define "yield_*" methods where the "*"
    matches the XML tag attribute of the elements to be handled
    by that parsing method.

    These methods are generator functions yielding (field, value) tuples.

    They can be static or class methods; as these classes are not intended
    to be instantiated, they should be one or the other.

    There are a number of generic parsing functions defined in this module
    which can simply be assigned as values to subclass "yield_*" functions:
    `yield_text`, `yield_int`, `yield_fraction`, and `yield_datatype`.

    `yield_datatype` is intended to be passed to `functools.partial`
    as is done in the definition of the SpellParser class.

    Once the XML structures have been parsed into tuples,
    post-processing code passes over it to group together like fields.

    There are two ways to implement post-processing for subclasses:

        - The simple way is to override _listify and/or _joined.
          These attributes indicate the fields which have multiple entries
          and should be combined, either by adding them to a list
          or by joining them with newlines into a single string.
        - If this is not sufficient, the _postprocess method itself
          can be overridden.
    """
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
        yield from cls._postprocess(cls._parse(node))

    @classmethod
    def _parse(cls, node):
        """Main parsing loop.

        Results yielded here can be manipulated by subclasses in _postprocess.
        """
        for element in node:
            try:
                parsefn = getattr(cls, 'yield_' + element.tag)
            except AttributeError:
                warning(f'NodeParser._parse: unknown tag "{element.tag}"')
                continue
            yield from parsefn(element, node)

    yield_name = staticmethod(yield_text)

    @classmethod
    def _postprocess(cls, it):
        """Subclass hook to manipulate results of processing.

        _postprocess hook is inserted into the iteration chain after other parsing is complete.
        It receives (key, value) pairs from it that, barring changes made here,
        become the contents of the dictionary being created by the calling function.

        E.G. `spell = dict(SpellParser.parse(spell_node)` would normally receive
        
            ('name', 'Magic Missile),
            ('level', 1),
            ('school', 'Evocation'),

        etc.; this function has the ability to modify that sequence.

        The default behaviour is to collect any fields in cls._listify
        into a list of objects, and to collect any fields in cls._join
        into a single newline-joined string.

        Overriding those attributes is all that should be necessary
        for most classes to implement proper post-processing.
        """
        listified = defaultdict(list)
        joined = defaultdict(list)
        for field, value in it:
            if field in cls._listify:
                listified[field].append(value)
            elif field in cls._join:
                joined[field].append(value)
            else:
                yield (field, value)

        yield from listified.items()
        for field, lines in joined.items():
            yield field, '\n'.join(lines)

    _listify = ()
    _join = ()

#### Derived parser classes
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

            Used by Monster.yield_speed().
            
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
        yield ('action', dict(MonsterActionParser.parse(element)))

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

    _listify = ('action')

class MonsterActionParser(NodeParser):
    _join = ('text',)
    re_damage = r'-?[0-9]+(?:d[0-9]+(?:[+-][0-9]+)?)?'
    re_attack_bonus = r'[+-][0-9]+'
    @classmethod
    def yield_attack(cls, element, node):
        # First of the fields is the name; this is redundant with the action 'name' element text.
        _, attack_bonus, damage = element.text.split('|')
        if attack_bonus:
            if not re.fullmatch(cls.re_attack_bonus, attack_bonus):
                warning(f'MonsterActionParser.yield_attack: validation fail for attack bonus "{attack_bonus}"')
            attack_bonus = int(attack_bonus)
            yield ('attack_bonus', attack_bonus)
        if damage:
            if not re.fullmatch(cls.re_damage, damage):
                warning(f'MonsterActionParser.yield_attack: validation fail for damage string "{damage}"')
            yield ('damage', damage)
    yield_text = yield_text

class SpellParser(NodeParser):
    yield_level = yield_int

    @staticmethod
    def yield_school(element, node):
        """School is abbreviated in the XML; translate it into a full word identifier."""
        yield ('school', datatypes.schools.reverse_lookup(element.text))

    @staticmethod
    def yield_ritual(element, node):
        yield ('ritual', element.text == 'YES')

    yield_time = partial(yield_datatype, datatypes.CastingTime)
    yield_range = partial(yield_datatype, datatypes.SpellRange)

    re_components = r'\bM \(([^)]*)\)'
    re_value = r'\b([0-9,]+)\s?([gs]p|gold pieces)\b'

    @classmethod
    def yield_components(cls, element, node):
        """Yields a dictionary with form resembling

        {'V': True,
         'M': "a sprig of rosemary"}

        >>> from dnd5edb.test import fakenode
        >>> test = lambda string: list(SpellParser.yield_components(fakenode('components', string), None))
        >>> test('S')
        [('components', {'S': True})]
        >>> test('V, S')
        [('components', {'V': True, 'S': True})]
        >>> test('V, S, M (a sliver of glass)')
        [('components', {'V': True, 'S': True, 'M': 'a sliver of glass'})]

        The value of components with monetary value is parsed and returned
        in one of two keys ('used' or 'consumed'):
        >>> test('V, S, M (a sprinkling of holy water, rare incense, and powdered ruby worth at least 1,000 gp)')
        [('components', {'V': True, 'S': True, 'M': 'a sprinkling of holy water, rare incense, and powdered ruby worth at least 1,000 gp', 'used': 1000})]
        >>> test('V, S, M (ruby dust worth 50 gp, which the spell consumes)')
        [('components', {'V': True, 'S': True, 'M': 'ruby dust worth 50 gp, which the spell consumes', 'consumed': 50})]

        Components with value given in sp will be parsed as tenths of gp:
        >>> test('S, M (a melee weapon worth at least 1 sp)')
        [('components', {'S': True, 'M': 'a melee weapon worth at least 1 sp', 'used': 0.1})]

        Some components are exceptions and are parsed with custom rules:
        >>> test('V, S, M (incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each)')
        [('components', {'V': True, 'S': True, 'M': 'incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each', 'consumed': 250, 'used': 200})]
        """
        text = element.text
        if text == None:
            return None

        components = re.sub(cls.re_components, 'M', text)
        components = re.split(',\s*', components)
        components = dict.fromkeys(components, True)

        material_details = re.search(cls.re_components, text)
        if material_details:
            if 'M' not in components:
                warning(f'yield_components: material details "{material_details}"'
                        + f' but no M in components "{text}"')
            material_details = material_details.groups()[0]
            components.update({'M': material_details})
            components.update(cls.parse_material_value(material_details))
        yield ('components', components)

    @classmethod
    def parse_material_value(cls, details):
        """Handle parsing of unusual material components manually.

        Examples and tests are found in SpellParser.yield_components.

        Returns a dictionary containing zero or more keys from the set
        {'used', 'consumed'}, indicating the respective value in gp.
        The values are of type `int` or `float`.
        """
        if details in datatypes.components_exceptions:
            return datatypes.components_exceptions[details]

        # Any spells with both used and consumed components with monetary value
        # are handled by exceptions, so here we just look for a monetary value
        # and then check for the string "consume"
        value = re.search(cls.re_value, details)
        if value:
            quantity, units = value.groups()
            # Monetary values sometimes contain commas, e.g. "1,000"
            quantity = quantity.translate({ord(','): None})
            quantity = int(quantity)
            if units == 'sp':
                quantity = quantity / 10

            if details.find('consume') > -1:
                return {'consumed': quantity}
            else:
                return {'used': quantity}

        return {}

    @staticmethod
    def yield_duration(element, node):
        """Yields tuples for 'concentration' and 'duration'.

        >>> from dnd5edb.test import fakenode
        >>> test = lambda string: list(SpellParser.yield_duration(fakenode('duration', string), None))
        >>> test('Concentration, up to 10 minutes')
        [('concentration', True), ('duration', SpellDuration('up to 10 minutes'))]
        >>> test('1 minute')
        [('concentration', False), ('duration', SpellDuration('1 minute'))]
        >>> test('Instantaneous, 1 hour')
        [('concentration', False), ('duration', SpellDuration('1 hour'))]
        """
        duration = element.text

        if duration is None:
            return False, None

        if duration[:15] == 'Concentration, ':
            conc, time = True, duration[15:]
        elif duration[:15] == 'Instantaneous, ':
            conc, time = False, duration[15:]
        else:
            conc, time = False, duration

        try:
            time = datatypes.SpellDuration(time)
        except KeyError as e:
            warning(f'parse_spell_duration: unknown spell duration in "{duration}".  Parsed conc: {conc}, time: {time}')

        yield ('concentration', conc)
        yield ('duration', time)

    @staticmethod
    def yield_classes(element, node):
        classes = element.text

        if classes is None:
            yield ('classes', [])
            return

        classes = re.split(',\s*', classes)
        classes = [c.strip() for c in classes]
        for c in classes:
            if c not in datatypes.caster_classes:
                warning(f'yield_classes: unknown caster class "{c}"')
        yield ('classes', sorted(classes))

    # Parsing of spell text and sources is handled in _postprocess
    yield_text = yield_text

    @classmethod
    def _postprocess(cls, results):
        """Post-processing for spell nodes.

        Collects `text` nodes, combines them,
        and splits them into singular `text` and `sources` nodes.
        """
        lines = []
        for field, value in results:
            if field == 'text':
                lines.append(value)
            else:
                yield (field, value)

        text, sources = cls._parse_spell_text(lines)
        yield ('text', text)
        yield ('sources', sources)

    @classmethod
    def _parse_spell_text(cls, lines):
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
        >>> parsed = SpellParser._parse_spell_text(text)
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
        >>> print(SpellParser._parse_spell_text(text)[1])
        (Reference(book="Player's Handbook", page=211),)

        >>> text = [
        ...     "Source: Xanathar's Guide to Everything p. 157, Elemental Evil Player's Companion p. 19", 
        ...     "Wayfinder's Guide to Eberron p. 107, Eberron: Rising from the Last War p. 50"]
        >>> print(SpellParser._parse_spell_text(text)[1])
        (Reference(book="Xanathar's Guide to Everything", page=157), Reference(book="Elemental Evil Player's Companion", page=19), Reference(book="Wayfinder's Guide to Eberron", page=107), Reference(book='Eberron: Rising from the Last War', page=50))
        """
        text_lines = []    # Accumulates lines of spell text in the for loop
        sources = []       # Accumulates Reference objects in the for loop
        in_sources = False # State that tracks if we're recording sources

        # Break out newlines in the list of strings
        lines = list(cls._expand_newlines(lines))

        for line in lines:
            if line is None:
                if in_sources:
                    in_sources = False
                continue

            line = line.strip()
            if line[:8] == 'Source: ':
                in_sources = True
                sources += cls._parse_spell_source(line[8:])
            elif in_sources:
                sources += cls._parse_spell_source(line)
            else:
                text_lines.append(line)

        return '\n'.join(text_lines), tuple(sources)

    @staticmethod
    def _expand_newlines(lines):
        r"""Split strings with newlines into multiple strings.

        >>> l = ["1\n2\n3", None, "4\n5\n6"]
        >>> list(SpellParser._expand_newlines(l))
        ['1', '2', '3', None, '4', '5', '6']
        """
        return chainfi([None] if l is None else l.split('\n') for l in lines)

    @classmethod
    def _parse_spell_source(cls, source):
        """Breaks source line into Reference(book, page) components.

        Returns a list of Reference objects.

        >>> source = "Xanathar's Guide to Everything, p. 152"
        >>> SpellParser._parse_spell_source(source)
        [Reference(book="Xanathar's Guide to Everything", page=152)]
        >>> SpellParser._parse_spell_source("")     # ignored because blank line
        []
        >>> source = "Xanathar's Guide to Everything p. 157, Elemental Evil Player's Companion p. 19, Wayfinder's Guide to Eberron p. 107, Eberron: Rising from the Last War p. 50"
        >>> SpellParser._parse_spell_source(source)
        [Reference(book="Xanathar's Guide to Everything", page=157), Reference(book="Elemental Evil Player's Companion", page=19), Reference(book="Wayfinder's Guide to Eberron", page=107), Reference(book='Eberron: Rising from the Last War', page=50)]
        >>> source = "Guildmasters' Guide to Ravnica"
        >>> SpellParser._parse_spell_source(source)
        [Reference(book="Guildmasters' Guide to Ravnica", page=None)]
        """
        source = source.strip()  # we're doing this more times than needed but nbd

        if source == "":
            # There are occasional blank lines, which we ignore
            return []

        m = re.match('^\s*(?P<book>.*?),?\s*p\.?\s*(?P<page>\d+)\s*(?P<extra>.*).*$', source)
        if m:
            book = m.groupdict()['book']
            if book not in datatypes.sources:
                warning(f"parse_spell_source: invalid source '{book}' parsed on line '{source}'")
            this_reference = [Reference(m.groupdict()['book'], int(m.groupdict()['page']))]
            extra = m.groupdict()['extra']
        elif source in datatypes.sources:  # some entries don't give page numbers
            this_reference = [Reference(source, None)]
            # Currently, pageless references only occur at the end of lines, so we can do this for now.
            extra = None
        else:
            warning(f"parse_spell_source: failed match on line '{source}'")
            return []

        if not extra:
            return this_reference
        if extra[0] == ',':
            return this_reference + cls._parse_spell_source(extra[1:].strip())
        else:
            warning(f"parse_spell_source: source '{source}': unknown extra '{extra}'")

    yield_roll = yield_text
