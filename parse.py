import re
from lxml import etree
from logging import debug, warning, error
from collections import namedtuple
from functools import reduce
from pprint import pprint, pformat
from textwrap import dedent
from fractions import Fraction
import dnd5edb
from dnd5edb import predicates
from itertools import groupby, chain
chainfi = chain.from_iterable

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
        darkling = tree.xpath("//monster[name/text() = 'Darkling']")[0]
        con = darkling.find('con')
        con.text = '12'

    @classmethod
    def parse_db(cls, db_file='FC5eXML/CoreOnly.xml'):
        """Parse XML file with lxml parser."""
        debug('Parsing xml...')
        parser = etree.XMLParser()
        with open(db_file, 'r') as xmlfile:
            tree = etree.parse(xmlfile, parser)
        debug('...done')
        cls.apply_errata(tree)
        return tree

    @classmethod
    def get_tree(cls, db_file='FC5eXML/CoreOnly.xml'):
        """Returns a tree at the top level of the parsed DB.

        Parses it if it has not already been processed.
        """
        if not cls.tree:
            cls.tree = cls.parse_db(db_file)
        return cls.tree

class Monster():
    """Collection of class functions for parsing monster nodes."""

    @classmethod
    def parse(cls, node):
        """Returns iterable of (field, value) pairs.

        The monster object dictionary can be updated with that iterable.
        """
        yield from cls.yield_if_present(node, 'name')
        yield from cls.yield_if_present(node, 'size')
        yield from cls.yield_if_present(node, 'type')
        yield from cls.yield_if_present(node, 'alignment')
        yield from cls.yield_if_present(node, 'ac', cls.yield_ac)
        yield from cls.yield_if_present(node, 'hp', cls.yield_hp)
        yield from cls.yield_if_present(node, 'speed', cls.yield_speed)
        for stat in ('str', 'dex', 'con', 'int', 'wis', 'cha'):
            yield from cls.yield_if_present(node, stat, cls.yield_int)
        yield from cls.yield_if_present(node, 'save', cls.yield_saves)
        yield from cls.yield_if_present(node, 'skill', cls.yield_skills)
        yield from cls.yield_if_present(node, 'resist', cls.yield_damage_types)
        yield from cls.yield_if_present(node, 'vulnerable', cls.yield_damage_types)
        yield from cls.yield_if_present(node, 'immune', cls.yield_damage_types)
        yield from cls.yield_if_present(node, 'conditionImmune', cls.yield_condition)
        yield from cls.yield_if_present(node, 'senses', cls.yield_senses)
        yield from cls.yield_if_present(node, 'passive', cls.yield_int)
        yield from cls.yield_if_present(node, 'description', cls.yield_text)
        yield from cls.yield_if_present(node, 'cr', cls.yield_fraction)
        yield from cls.yield_if_present(node, 'spells', cls.yield_text)
        yield from cls.yield_if_present(node, 'slots', cls.yield_text)

    @classmethod
    def yield_if_present(cls, node, field, fn=yield_args):
        field_node = node.find(field)
        if hasattr(field_node, 'text'):
            yield from fn(field, field_node.text)

    @classmethod
    def yield_ac(cls, field, text):
        """Yield ac attributes.

        If a numeric AC is parsed, it is yielded as `ac_num`.
        If information on armor is parsed in the parentheses following the AC,
        it is yielded as `armor`.
        In any case, the full text of the field is yielded as `ac`.
        """
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

    @classmethod
    def yield_hp(cls, field, text):
        """Assign to hp attributes.

        Similar to _assign_ac but assigns to `hp` and `hitdice` attributes.

        >>> d = dict(Monster.yield_hp('hp', '135 (18d10+36)'))
        >>> d['hp']
        135
        >>> d['hitdice']
        '18d10+36'
        >>> d = dict(Monster.yield_hp('hp', '0'))
        >>> d['hp']
        0
        >>> d['hitdice']
        Traceback (most recent call last):
            ...
        KeyError: 'hitdice'
        """
        m = re.match('^(\d+)(?: \(([^)]*)\))?$', text)
        if m is None:
            debug(f'Failed match for HP text "{text}"')
            return
        g = m.groups()
        yield ('hp', int(g[0]))
        if g[1]:
            yield ('hitdice', g[1])

    @classmethod
    def yield_speed(cls, field, text):
        """Parse speed fields into a dictionary.

        >>> test = lambda t: dict(Monster.yield_speed('', t))['speed']
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
        """
        movement_types = ['walk', 'fly', 'swim', 'climb', 'burrow']
        mtre = '(?:' + '|'.join(movement_types) + ')'
        vector_re_basic = f'(?:{mtre} )?\d+ ?ft\.?' # [movement_type] speed
        vector_re_hover = f'fly \d+ ft. \([Hh]over\)'
        vector_re_speed_first = f'\d+ ?ft\.? {mtre}'
        vector_just_a_number = f'\d+'
        vector_re = (f'(?:{vector_re_basic}|{vector_re_hover}|'
                      + f'{vector_re_speed_first}|{vector_just_a_number})')

        csv_match_re = f'^({vector_re})(?:, ({vector_re}))*$' # list of speeds, no ()

        def parse_vector(vector):
            """Parse a movement vector and return (type, speed).

            Used by Monster._assign_speed().
            
            >>> parse_vector('60 ft.')
            ('walk', 60)
            >>> parse_vector('climb 30 ft.')
            ('climb', 30)
            >>> parse_vector('yeet 10000 ft.')
            These don't work because it's an inner function.
            >>> parse_vector('fly 30 ft. (hover)')
            ('fly', 30)
            """
            # capture groups for type and speed
            parse_re = f'^(?:({mtre}) )?(\d+) ?ft\.?(?: \([Hh]over\))?$'
            parse_re_speed_first = f'^(\d+) ?ft\.? ({mtre})$'
            parse_re_just_a_number = '^(\d+)$'

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
            else:
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

    @classmethod
    def yield_int(cls, field, text):
        """Yield an integer that comprises the entirety of `text`."""
        yield (field, int(text))

    @classmethod
    def yield_saves(cls, field, text):
        """Yield ('saves', {..})

        Dictionary entries are a stat (eg 'str') and an integer.

        >>> test = lambda text: next(Monster.yield_saves('save', text))
        >>> test(None)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> test('Dex +5, Con +11, Wis +7, Cha +9')
        ('saves', {'dex': 5, 'con': 11, 'wis': 7, 'cha': 9})
        """
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

    @classmethod
    def yield_skills(cls, field, text):
        """Yield ('skills', {..})

        Dictionary entries are a skill (eg 'Athletics') and an integer.

        >>> test = lambda text: next(Monster.yield_skills('skill', text))
        >>> test(None)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> test('Perception +5')
        ('skills', {'Perception': 5})
        >>> test('History +7, Perception +11, Persuasion +8, Stealth +5')
        ('skills', {'History': 7, 'Perception': 11, 'Persuasion': 8, 'Stealth': 5})
        """
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
            error(f'yield_skills: {type(e)} "{e}" for text "{text}"')

        yield ('skills', skills)

    # damage types as they are used in the XML file
    # for resistances, vulnerabilities, and immunities
    damage_types = { # simple types which don't need remapping
        'bludgeoning', 'piercing', 'slashing',
        'poison', 'acid', 'fire', 'cold', 'radiant', 'necrotic',
        'lightning', 'thunder', 'force', 'psychic',

        'charmed', 'petrified', 'blinded', # should be in conditions but the DB is wrong

        'damage from spells',
        'piercing from magic weapons wielded by good creatures',
        "one of the following: acid, cold, fire, lightning or poison",
        "one of the following: acid, cold, fire, lightning, or poison",
    }
    damage_mappings = { # translation of complex fields
        'bludgeoning, piercing, and slashing from nonmagical attacks': {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning, piercing, and slashing damage from nonmagical weapons": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning, piercing, slashing from nonmagical attacks": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning, piercing, and slashing damage from nonmagical attacks": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical weapons": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning, piercing and slashing from nonmagical attacks": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning, piercing, and slashing that is nonmagical": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "bludgeoning from nonmagical attacks": {
            'types': {
                'nonmagical bludgeoning'}},

        "fire, bludgeoning, piercing, and slashing from nonmagical attacks": {
            'types': {
                'nonmagical fire',
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},
        "cold, fire, lightning, bludgeoning, piercing and slashing that is nonmagical": {
            'types': {
                'nonmagical cold',
                'nonmagical fire',
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'}},

        'non magical bludgeoning, piercing, and slashing (from stoneskin)': {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'},
            'notes': {
                'from stoneskin': [
                    'nonmagical bludgeoning',
                    'nonmagical piercing',
                    'nonmagical slashing']}},
        "nonmagical bludgeoning, piercing, slashing (from stoneskin)": {
            'types': {
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'},
            'notes': {
                'from stoneskin': [
                    'nonmagical bludgeoning',
                    'nonmagical piercing',
                    'nonmagical slashing']}},

        "bludgeoning, piercing, and slashing from nonmagical attacks that aren't silvered": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical attacks that aren’t silvered": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, slashing from nonmagical attacks that aren't silvered": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical/nonsilver weapons": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical attacks not made with silvered weapons": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical weapons that aren't silvered": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, and slashing damage from nonmagical attacks that aren't silvered": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "bludgeoning, piercing, and slashing damage from nonmagical attacks that aren't silvered weapons": {
            'types': {
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},
        "slashing damage from nonmagical attacks not made with silvered weapons": {
            'types': {
                'nonmagical nonsilver slashing'}},

        "lightning, poison, bludgeoning, piercing, sand slashing from non-magical attacks that aren't adamantine or silvered": {
            'types': {
                'lightning',
                'poison',
                'nonmagical nonsilver bludgeoning',
                'nonmagical nonsilver piercing',
                'nonmagical nonsilver slashing'}},

        "bludgeoning, piercing, and slashing from nonmagical attacks that aren't adamantine": {
            'types': {
                'nonmagical nonadamantine bludgeoning',
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},
        "bludgeoning, piercing, and slashing damage from nonmagical attacks not made with adamantine weapons": {
            'types': {
                'nonmagical nonadamantine bludgeoning',
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},
        "bludgeoning, piercing, slashing from nonmagical attacks that aren't adamantine": {
            'types': {
                'nonmagical nonadamantine bludgeoning',
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical attacks that aren’t adamantine": {
            'types': {
                'nonmagical nonadamantine bludgeoning',
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},
        "bludgeoning, piercing, and slashing from nonmagical weapons that aren't adamantine": {
            'types': {
                'nonmagical nonadamantine bludgeoning',
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},
        "piercing and slashing from nonmagical attacks that aren't adamantine": {
            'types': {
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},

        "fire, bludgeoning, piercing, and slashing from metal weapons": {
            'types': {
                'fire',
                'metal bludgeoning',
                'metal piercing',
                'metal slashing'}},

        "bludgeoning, piercing, and slashing from magic weapons": {
            'types': {
                'magical bludgeoning',
                'magical piercing',
                'magical slashing'}},

        "bludgeoning, piercing, and slashing while in dim light or darkness": {
            'types': {
                'bludgeoning while in dim light or darkness',
                'piercing while in dim light or darkness',
                'slashing while in dim light or darkness'}},
        "bludgeoning, piercing, and slashing from nonmagical attacks while in dim light or darkness": {
            'types': {
                'nonmagical bludgeoning while in dim light or darkness',
                'nonmagical piercing while in dim light or darkness',
                'nonmagical slashing while in dim light or darkness'}},

        "while wearing the mask of the dragon queen: acid, cold, lightning, poison": {
            'types': {
                'acid', 'cold', 'lightning', 'poison',
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing'},
            'notes': {
                'While wearing the mask of the Dragon Queen': [
                    'acid', 'cold', 'lightning', 'poison']}},
        "while wearing the mask of the dragon queen: fire": {
            'types': {'fire'},
            'notes': {'while wearing the mask of the dragon queen': 'fire'}},

        "cold (while wearing the ring of winter)": {
            'types': {'cold'},
            'notes': {'while wearing the ring of winter': 'cold'}},

        'posion': {
            'types': {'poison'}},
    }

    @classmethod
    def yield_damage_types(cls, field, text):
        """Yields the `field` and the damage types that apply to it for `text`.

        `field` can be "resist", "vulnerable", or "immune"

        Yield format e.g. ('resist': {..})

        May also yield notes in the form ('resist_notes': {..})

        >>> test = lambda text: list(Monster.yield_damage_types('resist', text))
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
        if text == None:
            return

        found, notfound = [], []

        # First, parse the text, first along semicolon delimeters,
        # then along commas
        scsvs = re.split('; ?', text.lower()) #Semi-Colon-Separated Values
        scsvs = map(str.strip, scsvs)

        damage_types = set()
        damage_types.update(cls.damage_types)
        damage_types.update(cls.damage_mappings.keys())

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
            if i in cls.damage_mappings.keys():
                try:
                    field_contents += cls.damage_mappings[i]['types']
                    field_notes.update(cls.damage_mappings[i]['notes'])
                except KeyError:
                    None
            else:
                field_contents.append(i)

        if field_contents:
            yield (field, set(field_contents))
        if field_notes:
            yield (f'{field}_notes', field_notes)

    @classmethod
    def yield_condition(cls, field, text):
        """Parse field containing a set of conditions and yield the result.

        >>> test = lambda text: dict(Monster.yield_condition('conditionImmune', text))
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
            raise Exception(f'Unmatched CSV "{csv}" in field text "{text}"')

        try:
            yield (field, set(process_csv(csv) for csv in csvs))
        except Exception as e:
            warning(f'yield_condition: {e.args[0]}')

    @classmethod
    def yield_senses(cls, field, text):
        """Parse 'senses' fields and yield the results.

        >>> test = lambda text: dict(Monster.yield_senses('senses', text))
        >>> test(None)
        {}
        >>> next(Monster.yield_senses('senses', None))
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
                 'senses_notes': {'darkvision': 'can see invisible creatures to same range'}}
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

    @classmethod
    def yield_int(cls, field, text):
        """Parse integer values and yield (field, value)

        >>> test = lambda text: dict(Monster.yield_int('passive', text))
        >>> test(None)
        {}
        >>> test('42')
        {'passive': 42}
        >>> from unittest import TestCase
        >>> with TestCase.assertLogs(_) as cm:
        ...     print(test('seven'))
        ...     print(cm.output)
        {}
        ['WARNING:root:yield_int: failed to parse text "seven"']
        """
        if text == None:
            return

        try:
            yield (field, int(text))
        except ValueError:
            warning(f'yield_int: failed to parse text "{text}"')

    @classmethod
    def yield_text(cls, field, text):
        """Just yield the text field."""
        if text is None:
            return

        yield (field, text)

    @classmethod
    def yield_fraction(cls, field, text):
        """Convert fractional text field to float and yield (field, result)

        >>> test = lambda text: dict(Monster.yield_fraction('cr', text))
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
        if text == None:
            return

        try:
            yield (field, float(Fraction(text)))
        except ValueError:
            warning(f'yield_fraction: failed to parse text "{text}"')

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

    @classmethod
    def parse_casting_time(cls, time):
        #TODO: write this, validate
        # Why are there None values for this?
        return time

    @classmethod
    def parse_spell_range(cls, r):
        #TODO: write this, validate
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
        #TODO: add validation
        if duration is None:
            return False, None

        if duration[:15] == 'Concentration, ':
            return True, duration[15:]
        else:
            return False, duration

    @classmethod
    def parse_spell_classes(cls, classes):
        if classes is None:
            return []
        classes = re.split(',\s*', classes)
        classes = [c.strip() for c in classes]
        return sorted(classes)

    @classmethod
    def parse_spell_source(cls, source):
        """Breaks source line into Reference(book, page) components.

        >>> source = "Xanathar's Guide to Everything, p. 152"
        >>> Spell.parse_spell_source(source)
        Reference(book="Xanathar's Guide to Everything", page=152)
        >>> source = "Player's Handbook, p. 277 (spell)"
        >>> Spell.parse_spell_source(source)
        Reference(book="Player's Handbook", page=277)
        >>> source = "Xanathar's Guide to Everything, p. 20 (class feature)"
        >>> Spell.parse_spell_source(source) # ignored because is class feature
        >>> Spell.parse_spell_source("")     # ignored because blank line
        """
        if source == "":
            # There are occasional blank lines, which we ignore
            return None
        m = re.match('^(?P<book>.*?),?\s*p\.?\s*(?P<page>\d+)\s*(?P<extra>.*).*$', source)
        if m is None:
            warning(f"parse_spell_source: failed match on line '{source}'")
            return None
        #debug(book)
        extra = m.groupdict()['extra']
        if extra == '(spell)' or not extra:
            return Reference(m.groupdict()['book'], int(m.groupdict()['page']))
        if extra == '(class feature)':
            return None
        else:
            warning(f"parse_spell_source: unknown extra '{extra}'")

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
        """
        sources = []
        def process(lines):
            in_sources = False # State that tracks if we're recording sources
            lines = list(Spell.expand_newlines(lines))

            for line in lines:
                if line is None:
                    if in_sources:
                        in_sources = False
                    continue

                line = line.strip()
                if line[:8] == 'Source: ':
                    in_sources = True
                    parsed = cls.parse_spell_source(line[8:])
                elif in_sources:
                    parsed = cls.parse_spell_source(line)
                else:
                    yield line
                    continue
                if parsed is not None:
                    sources.append(parsed)
        text = '\n'.join(process(lines))
        return text, tuple(sources)
