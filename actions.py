"""Handle actions, in particular, attack actions.

A bit of exploration in here:
>>> from repltools import m, p
>>> from pprint import pprint
>>> from functools import partial
>>> pprint = partial(pprint, width=200)
>>> from collections import defaultdict
>>> from re import fullmatch

>>> have_ma = m.where(actions=p.contains('Multiattack'))
>>> have_ma[0]
Monster(Aberrant Spirit: M Unaligned aberration, --CR 40HP/-- 0AC (walk 30, fly 30))
>>> have_ma[0].actions.attack_form
('default', "The aberration makes a number of attacks equal to half this spell's level (rounded down).")

>>> def groupeddict(it):
...     d = defaultdict(list)
...     for k, v in it:
...         d[k].append(v)
...     return d
>>> histogram = lambda d: {k: len(v) for k, v in d.items()}

>>> grouped_by_form = groupeddict(n.actions.attack_form.summary for n in have_ma)
>>> histogram(grouped_by_form)
{'ByHalfSpellLevel': 9, 'Named': 221, 'Default': 426, 'AnyMelee': 105, 'ArtAAndArtB': 195, 'ArtAAndArtBOrC': 23, 'AOrB': 20, 'WithNamed': 44, 'MeleeOrRanged': 28, 'Any': 14, 'ColonAndPeriod': 1}

>>> #pprint(grouped_by_form['ColonAndPeriod'][:40])
>>> pprint(grouped_by_form['Default'][:40])
>>> #pprint(grouped_by_form['a_and_art_b'][:40])
>>> #pprint(grouped_by_form['Named'][:40])

What's the deal with any_melee
>>> any_melee = [n for n in m.where(actions=p.contains('Multiattack'))
...              if n.actions.attack_form.form == 'AnyMelee']
>>> #pprint([n.actions for n in any_melee][:20])
"""
import re
from dnd5edb import calc
from functools import cached_property
from logging import warning

class Actions(dict):
    """Data and methods for the actions of a particular monster.

    Mostly provides multiattack calculation functionality.

    Functions like a dict of dictionaries but provides additional functionality.

    Multiattack information is parsed when used and cached for future access.

    Methods dpr_* implement parsing of various multi
    """
    @property
    def dpr(self):
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

        Checking for errors...
        >>> from unittest import TestCase
        >>> with TestCase.assertLogs(_) as cm:
        ...     _ = [n.dpr(10) for n in m]
        ...     print('\n'.join(cm.output))
        """
        return self.attack_form.dpr

    @cached_property
    def attacks(self):
        """Subset of Actions which have `attack_bonus` and `damage` entries."""
        return {name: Attack(attack) for name, attack in self.items()
                if 'attack_bonus' in attack and 'damage' in attack}

    @cached_property
    def multiattack_text(self):
        try:
            return self['Multiattack']['text']
        except KeyError:
            return None

    @cached_property
    def attack_form(self):
        """Matches multiattack text to one of the REs in attack_forms.keys().

        Returns an instantiated object of the class keyed by that RE.
        """
        return AttackForm(self)

attack_forms = {} # gets filled up by AttackForm.__init_subclass__

class AttackForm:
    """Base class for attack set classes."""
    def __init__(self, actions):
        """Matches multiattack text to one of the REs in attack_forms.keys().

        Typecasts `self` to the class keyed by that RE.
        """
        self.actions = actions

        if actions.multiattack_text is None:
            self.__class__ = attack_forms[None]
            self.match = None
            return

        for regexp, form_class in attack_forms.items():
            match = re.fullmatch(regexp, actions.multiattack_text)
            if match:
                self.__class__ = form_class
                self.match = match
                return

        raise Exception(f'Attack_Form.__init__: no match found.  Actions: {actions}')

    def __repr__(self):
        return f'{self.form}({repr(getattr(self.match, "string", None))})'

    @property
    def summary(self):
        return (self.form, getattr(self.match, "string", None))

    @property
    def form(self):
        return self.__class__.__name__

    # for some reason, the main (parent) class isn't passed to this hook
    def __init_subclass__(subclass):
        """Hook used to ensure that order of created subclasses is maintained.

        This order will determine the priority of the various regexps.
        """
        attack_forms.update({subclass.re: subclass})

    def dpr(self, target_ac):
        """Redefined in handler subclasses."""
        return None

    def _match_attack(self, attack_name):
        """Matches the `attack_name` against one of the attacks in `self.actions`."""
        for name, attack in self.actions.attacks.items():
            if attack_name.lower().rstrip('s') in name.lower():
                return attack
        return None

    def _validate(self):
        r"""Validates the `self.match` data and returns interpreted group match data.

        Validation/interpretation steps:
        * /num\d+/ groups are cast to int
        * "total" group is cast to int
        * confirms that `total` is the sum of all /num\d+/ groups
        * finds corresponding attacks for /type\d*/ groups

        Return value is an object with zero or more of the following attributes:

        * a\1count: int(/num(\d+)/)
        * total: int(/total/)
        * a\1name: /type(\d+)/
        * for each /type(\d+)/ group, a corresponding /a\1attack/ group is returned
            * that groups contains the matching attack from `self.actions.attacks`

        Returns None instead if attack matching fails.
        """
        w = lambda m: warning(f'{self.__class__.__name__}._validate: {m}.  Match: {self.match}')
        ret = {}
        counts = []
        for key, val in self.match.groupdict().items():
            if re.fullmatch('num\d+', key):
                anum = int(key[3:])
                count = numberwords[val]
                ret[f'a{anum}count'] = count
                counts.append(count)
                continue
            if key == 'total':
                ret['total'] = numberwords[val]
                continue
            if re.fullmatch('type\d+', key):
                anum = int(key[4:])
                ret[f'a{anum}name'] = val
                attack = self._match_attack(val)
                if attack:
                    ret[f'a{anum}attack'] = attack
                    continue
                w(f'attack match for "{val}" is None; attacks: {self.actions.attacks}')
                return None
            if key == 'mname':
                ret['mname'] = val
                continue

        if 'total' in ret:
            if sum(counts) != ret['total']:
                w(f'validation of total failed: {"+".join(counts)} != {ret["total"]}')

        return Validated(**ret)

class Attack(dict):
    def dpr(self, target_ac):
        if 'attack_bonus' in self and 'damage' in self:
            return calc.dpr(target_ac, self['attack_bonus'], self['damage'])
        return None

class Validated:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

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
re_article = r'(?:a|its|his|her)?' # We should be able to just ignore articles like a, its, his, etc.

re_name = r'(?P<mname>[^.]+)'
form_text = lambda form: (form.__class__, form.match.string) # translates multiattack output into convenient form

# AttackForm subclasses defined in order of parsing priority.
# AttackForm.__init__ will try to match the `re` attribute of each of these in this order.
class Any(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<total>{re_num}) (?:weapon )?attacks\.'
    # we can select the most effective attacks from all options
class AnyMelee(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<num>{re_num}) melee attacks\.'
    # we can select the most effective attacks from all melee options.
    # melee options seem to be consistently indicated with 'Melee' at the beginning of the action text.
class AnyRanged(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<num>{re_num}) ranged attacks\.'
    # we can select the most effective attacks from all ranged options
    # ranged options seem to be consistently indicated with 'Melee' at the beginning of the action text.
class MeleeOrRanged(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<num_melee>{re_num}) melee attacks or (?P<num_ranged>{re_num}) ranged attacks\.'
    # choose max of averages of optimal ranged and optimal melee attacks
class Named(AttackForm):
    """A varying number of attacks of a named type.

    >>> from repltools import m
    >>> liff = m.where(name='Lifferlas')[0]
    >>> liff.actions.attack_form
    Named('Lifferlas makes two slam attacks.')
    >>> {ac: liff.dpr(ac) for ac in (10, 15, 20)}
    {10: 24.65, 15: 17.4, 20: 10.15}
    """
    re = f'(?P<mname>[^.]+) makes (?P<num1>{re_num}) (?P<type1>\w+) attacks\.'
    def dpr(self, target_ac):
        """Check if `type` matches an attack action name; otherwise fail."""
        v = self._validate()
        if v is None:
            return None
        return v.a1count * v.a1attack.dpr(target_ac)

class WithNamed(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<num>{re_num}) (?:melee |ranged )?attacks with {re_article} (?P<type>\w+)\.'
    # check if `type` matches an attack action name; otherwise fail
    # same handler as 'named'
class ArtAAndArtBOrC(AttackForm):
    re = (f'(?P<mname>[^.]+) makes (?P<total>{re_num}) attacks: '
          + f'(?P<num1>{re_num}) with {re_article} (?P<type1>[^,.]+) '
          + f'and (?P<num2>{re_num}) with {re_article} (?P<type2>[^,.]+) or (?P<type3>[^,.]+)\.')
    # similar to `a_and_art_b` but there's a choice between type2 and type3 for the second attack.
class ArtAAndArtB(AttackForm):
    """Attacks of two different types with articles or pronouns preceding them.

    >>> from repltools import m
    >>> bear = m.where(name='Brown Bear')[0]
    >>> (bear.actions.attack_form)
    ArtAAndArtB('The bear makes two attacks: one with its bite and one with its claws.')
    >>> {ac: bear.dpr(ac) for ac in (10, 15, 20)}
    {10: 16.575, 15: 11.7, 20: 6.825}
    """
    re = (f'(?P<mname>[^.]+) makes (?P<total>{re_num}) attacks: '
          + f'(?P<num1>{re_num}) with {re_article} (?P<type1>[^,.]+) '
          + f'and (?P<num2>{re_num}) with {re_article} (?P<type2>[^,.]+)\.')
    def dpr(self, target_ac):
        """Sum of DPR from two different attacks."""
        v = self._validate()

        if v is None:
            return None

        return v.a1count * v.a1attack.dpr(target_ac) + v.a2count * v.a2attack.dpr(target_ac)

class AOrB(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<num1>{re_num}) (?P<type1>[^,.]+) attacks or (?P<num2>{re_num}) (?P<type2>[^,.]+) attacks\.'
    # check type1 & type2; fail if check fails; calculate optimal damage
class ColonAndPeriod(AttackForm):
    re = f'(?P<mname>[^.]+) makes (?P<total>{re_num}) attacks: (?P<num1>{re_num}) with (?P<type1>[^,.]+) and (?P<num2>{re_num}) with (?P<type2>[^,.]+)\.'
    # parse num1 and num2 as numbers; check type1 and type 2 against attack action names; otherwise fail
class ByHalfSpellLevel(AttackForm):
    re = f"{re_name} makes a number of attacks equal to half this spell's level \(rounded down\)\."
    # Auto-fail since we don't know the spell level.
    # hmmmmm or maybe default to 1 attack of any kind?
class Default(AttackForm):
    re = r'.*(?:\n.*)*'
class NoMultiattack(AttackForm):
    re = None
    def dpr(self, target_ac):
        if self.actions.attacks:
            return max(attack.dpr(target_ac)
                       for name, attack in self.actions.attacks.items())
        return None
# failures are rendered with uhhh '??' I guess.
# however, we can will program in many of these as exceptional cases;
#   these are found by checking the monster name before we reach this point.
