"""Handle actions, in particular, attack actions.

A bit of exploration in here:
>>> from repltools import m, p
>>> from pprint import pprint
>>> from functools import partial
>>> pprint = partial(pprint, width=200)
>>> from collections import defaultdict
>>> from re import fullmatch
>>> have_ma = m.where(action=p.contains('Multiattack'))
>>> have_ma[0]
Monster(Aberrant Spirit: M Unaligned aberration, --CR 40HP/-- 0AC (walk 30, fly 30))
>>> get_ma_text = lambda n: n.action['Multiattack']['text']
>>> form_text(parse_multiattack(get_ma_text(have_ma[0])))
('default', "The aberration makes a number of attacks equal to half this spell's level (rounded down).")

>>> def groupeddict(it):
...     d = defaultdict(list)
...     for k, v in it:
...         d[k].append(v)
...     return d
>>> histogram = lambda d: {k: len(v) for k, v in d.items()}

>>> grouped_by_re = groupeddict(form_text(parse_multiattack(get_ma_text(n))) for n in have_ma)
>>> histogram(grouped_by_re)
>>> #pprint(grouped_by_re['colon_and_period'][:40])
>>> pprint(grouped_by_re['default'][:40])
>>> #pprint(grouped_by_re['a_and_art_b'][:40])
>>> #pprint(grouped_by_re['named'][:40])

What's the deal with any_melee
>>> any_melee = [n for n in m.where(action=p.contains('Multiattack'))
...              if parse_multiattack(n.action['Multiattack']['text'])['form'] == 'any_melee']
>>> #pprint([n.action for n in any_melee][:20])
"""
import re
from dnd5edb import calc
from functools import cached_property
from logging import warning
round4 = lambda x: round(x, 4) if x is not None else None

class Actions(dict):
    """Data and methods for the actions of a particular monster.

    Mostly provides multiattack calculation functionality.

    Functions like a dict of dictionaries but provides additional functionality.

    Multiattack information is parsed when used and cached for future access.

    Methods dpr_* implement parsing of various multi
    """
    @cached_property
    def multiattack(self):
        if 'Multiattack' in self:
            text = self['Multiattack']['text']
            return parse_multiattack(text)
        else:
            return None

    def dpr(self, target_ac):
        r"""Calculate average DPR of the monster vs a given AC.

        >>> from repltools import m
        >>> m.where(name='Wolf')[0].dpr(10)
        5.25
        >>> m.where(name='Wolf')[0].dpr(15)
        3.5
        >>> m.where(name='Wolf')[0].dpr(20)
        1.75

        Even against very high AC, there's still some chance of hitting with a nat 20.
        Note that extra critical damage is not currently included.
        >>> m.where(name='Wolf')[0].dpr(40)
        0.35

        Works for most multiattack creatures as well:
        >>> three_dprs = lambda monster: {ac: monster.dpr(ac) for ac in (10, 15, 20)}
        >>> three_dprs(m.where(name='Brown Bear')[0])
        {10: 16.575, 15: 11.7, 20: 6.825}
        >>> three_dprs(m.where(name='Lifferlas')[0])
        {10: 24.65, 15: 17.4, 20: 10.15}

        Checking for errors...
        >>> from unittest import TestCase
        >>> with TestCase.assertLogs(_) as cm:
        ...     _ = [n.dpr(10) for n in m]
        ...     print('\n'.join(cm.output))
        """
        if self.multiattack:
            dpr = getattr(self, 'dpr_' + self.multiattack['form'], None)
            if dpr:
                return round4(dpr(self.multiattack['match'], target_ac))
        else:
            if self.attacks:
                return round4(max(calc.dpr(target_ac, attack['attack_bonus'], attack['damage'])
                              for name, attack in self.attacks.items()))
        return None

    def dpr_named(self, match, target_ac):
        """Returns DPR for a parsed multiattack string with the 'named' form.

        'named': f'(?P<mname>[^.]+) makes (?P<num>{re_num}) (?P<type>\w+) attacks\.'
        """
        groupdict = match.groupdict()
        num = numberwords[groupdict['num']]
        attack_name = groupdict['type']

        for name, attack in self.attacks.items():
            if attack_name.lower() in name.lower():
                return num * calc.dpr(target_ac, attack['attack_bonus'], attack['damage'])
        warning(f'Actions.dpr_named: failed to match attack name "{attack_name}" for match "{match}"; self.attacks: {self.attacks}')
        return None

    @cached_property
    def attacks(self):
        """Subset of Actions which have `attack_bonus` and `damage` entries."""
        return {name: attack for name, attack in self.items()
                if 'attack_bonus' in attack and 'damage' in attack}

class RESelect(dict):
    """Instantiates a callable which atttempts matching `text` with a sequence of REs.

    If a match succeeds, returns a dict containing:
    * form: the label given to this RE
    * match: the Match object returned by re.fullmatch
    * regexp: the RE matched against
    * text: the text which matched successfully

    If a match fails, `form` is `default` and `match` and `regexp` are both `None`.

    >>> selector = RESelect({'one': r'.*one.*', 'two': r'.*two.*'})
    >>> form_text(selector('onetwo'))
    ('one', 'onetwo')
    >>> form_text(selector('twoone'))
    ('one', 'twoone')
    >>> selector = RESelect({'two': r'.*two.*', 'one': r'.*one.*'})
    >>> form_text(selector('onetwo'))
    ('two', 'onetwo')
    >>> form_text(selector('twoone'))
    ('two', 'twoone')
    """
    def __init__(self, re_dict):
        super().__init__(re_dict)

    def __call__(self, text):
        for form, regexp in self.items():
            match = re.fullmatch(regexp, text)
            if match:
                return self._handle(form, match, regexp, text)
        return self._handle_default(text)

    def _handle(self, form, match, regexp, text):
        return {'form': form, 'match': match, 'regexp': regexp, 'text': text}

    def _handle_default(self, text):
        return {'form': 'default', 'match': None, 'regexp': None, 'text': text}

### parsing constants
numberwords = {
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    }
re_num = '|'.join(numberwords)
re_article = r'(?:a|its|his|her)?'
re_name = r'(?P<mname>[^.]+)'
form_text = lambda d: (d['form'], d['text']) # translates multiattack output into convenient form
parse_multiattack = RESelect({
    'any': f'(?P<mname>[^.]+) makes (?P<total>{re_num}) (?:weapon )?attacks\.',
        # we can select the most effective attacks from all options
    'any_melee': f'(?P<mname>[^.]+) makes (?P<num>{re_num}) melee attacks\.',
        # we can select the most effective attacks from all melee options.
        # melee options seem to be consistently indicated with 'Melee' at the beginning of the action text.
    'any_ranged': f'(?P<mname>[^.]+) makes (?P<num>{re_num}) ranged attacks\.',
        # we can select the most effective attacks from all ranged options
        # ranged options seem to be consistently indicated with 'Melee' at the beginning of the action text.
    'melee_or_ranged': f'(?P<mname>[^.]+) makes (?P<num_melee>{re_num}) melee attacks or (?P<num_ranged>{re_num}) ranged attacks\.',
        # choose max of averages of optimal ranged and optimal melee attacks
    'named': f'(?P<mname>[^.]+) makes (?P<num>{re_num}) (?P<type>\w+) attacks\.',
        # check if `type` matches an attack action name; otherwise fail
    'with_named': f'(?P<mname>[^.]+) makes (?P<num>{re_num}) (?:melee |ranged )?attacks with {re_article} (?P<type>\w+)\.',
        # check if `type` matches an attack action name; otherwise fail
        # same handler as 'named'
    'art_a_and_art_b_or_c': f'(?P<mname>[^.]+) makes (?P<total>{re_num}) attacks: '
        + f'(?P<num1>{re_num}) with {re_article} (?P<type1>[^,.]+) '
        + f'and (?P<num2>{re_num}) with {re_article} (?P<type2>[^,.]+) or (?P<type3>[^,.]+)\.',
        # similar to `a_and_art_b` but there's a choice between type2 and type3 for the second attack.
    'art_a_and_art_b': f'(?P<mname>[^.]+) makes (?P<total>{re_num}) attacks: '
        + f'(?P<num1>{re_num}) with {re_article} (?P<type1>[^,.]+) '
        + f'and (?P<num2>{re_num}) with {re_article} (?P<type2>[^,.]+)\.',
        # we should be able to just ignore articles like a, its, his, etc.  Check type1 and type2 against attack action names.
        # if they don't all match, we're still okay if there are only two attack actions
        # otherwise, fail
    'a_or_b': f'(?P<mname>[^.]+) makes (?P<num1>{re_num}) (?P<type1>[^,.]+) attacks or (?P<num2>{re_num}) (?P<type2>[^,.]+) attacks\.',
        # check type1 & type2; fail if check fails; calculate optimal damage
    'colon_and_period': f'(?P<mname>[^.]+) makes (?P<total>{re_num}) attacks: (?P<num1>{re_num}) with (?P<type1>[^,.]+) and (?P<num2>{re_num}) with (?P<type2>[^,.]+)\.',
        # parse num1 and num2 as numbers; check type1 and type 2 against attack action names; otherwise fail
    'by_half_spell_level': f"{re_name} makes a number of attacks equal to half this spell's level \(rounded down\)\.",
        # Auto-fail since we don't know the spell level.
        # hmmmmm or maybe default to 1 attack of any kind?
    })
# failures are rendered with uhhh '??' I guess.
# however, we can will program in many of these as exceptional cases;
#   these are found by checking the monster name before we reach this point.
