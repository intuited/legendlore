import re
from logging import debug, warning, error

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
        yield from cls.yield_if_present(node, 'resist', cls.yield_resistances)

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
        "slashing damage from nonmagical attacks not made with silvered weapons": {
            'types': {
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
        "piercing and slashing from nonmagical attacks that aren't adamantine": {
            'types': {
                'nonmagical nonadamantine piercing',
                'nonmagical nonadamantine slashing'}},

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
    }

    @classmethod
    def yield_resistances(cls, field, text):
        """Yield ('resistances': {..})

        Set entries are strings.

        >>> from pprint import pprint
        >>> test = lambda text: list(Monster.yield_resistances('resist', text))
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
                csvs = map(str.strip, csvs)
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
