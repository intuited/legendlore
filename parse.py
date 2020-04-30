import re
from logging import debug, warning, error

def yield_args(*args):
    yield args

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

    # Pretty sure I don't need this
    # def _assign_csv(self, field, text):
    #     """Parse comma-separated values and assign them as a list.

    #     >>> mutate_blank(Monster._assign_csv, 'speed',
    #     ...              '40 ft., fly 80 ft., swim 40 ft.').speed
    #     ['40 ft.', 'fly 80 ft.', 'swim 40 ft.']
    #     """


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
