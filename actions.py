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
ByHalfSpellLevel("The aberration makes a number of attacks equal to half this spell's level (rounded down).")

>>> def groupeddict(it):
...     d = defaultdict(list)
...     for k, v in it:
...         d[k].append(v)
...     return d
>>> histogram = lambda d: {k: len(v) for k, v in d.items()}

>>> grouped_by_form = groupeddict(n.actions.attack_form.summary for n in have_ma)
>>> histogram(grouped_by_form)
{'ByHalfSpellLevel': 9, 'Named': 248, 'Default': 323, 'AnyMelee': 107, 'WithNamed2Options': 14, 'ArtAAndArtB': 204, 'ArtAAndArtBOrC': 21, 'AOrB': 20, 'WithNamed': 54, 'MeleeOrRanged': 28, 'Any': 15, 'AttacksWithNamed': 27, 'MakesAAndB': 6, 'TwiceArtAAndArtB': 6, 'NamedAndUses': 4}

>>> pprint(grouped_by_form['Default'][:40])
>>> pprint(grouped_by_form['ByHalfSpellLevel'][:40])

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
            if regexp is None:
                continue
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

    # changed to '>' or '>=' for classes which have additional effects
    dpr_confidence='~='

    def dpr(self, target_ac):
        """Redefined in handler subclasses."""
        v = self._validate()
        if v is None:
            return None
        return self._calc_dpr(target_ac, v)

    def _calc_dpr(self, target_ac, v):
        """Called by dpr() if it successfully validates.

        Should be overridden by handler subclasses.
        """
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
                count = numberwords[val] if val else 1 # sometimes we match conditionally with "twice"
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
            # sometimes we use `total` without `num*` groups
            if counts and sum(counts) != ret['total']:
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
    'once': 1,
    'two': 2,
    'twice': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    }
re_num = '|'.join(numberwords)
re_article = r'(?:a|its|his|her)? ?' # We should be able to just ignore articles like a, its, his, etc.

re_name = r'(?P<mname>[^,.]+)'
re_total = f'(?P<total>{re_num})'

re_count = lambda n: f'(?P<num{n}>{re_num})'
re_type_word = lambda n: f'(?P<type{n}>\w+(?:\s\w+)?)'
re_type_phrase = lambda n: f'(?P<type{n}>[^,.]+)'

# AttackForm subclasses defined in order of parsing priority.
# AttackForm.__init__ will try to match the `re` attribute of each of these in this order.
class Any(AttackForm):
    """MONSTER makes NUM attacks.

    >>> from repltools import m
    >>> zombo = m.where(name='Frost Giant Zombie')[0]
    >>> zombo.actions.attack_form
    Any('The zombie makes two weapon attacks.')
    >>> {ac: zombo.dpr(ac) for ac in range(10, 31, 2)}
    {10: 53.2, 12: 53.2, 14: 47.6, 16: 42.0, 18: 36.4, 20: 30.8, 22: 25.2, 24: 19.6, 26: 14.0, 28: 8.4, 30: 2.8}
    """
    re = f'{re_name} makes (?P<total>{re_num}) (?:weapon )?attacks\.?'
    # we can select the most effective attacks from all options
    def _calc_dpr(self, target_ac, v):
        return v.total * max(attack.dpr(target_ac) for attack in self.actions.attacks.values())
class AnyMelee(AttackForm):
    """MONSTER makes NUM melee attacks.

    >>> from repltools import m
    >>> fanatic = m.where(name='Cult Fanatic')[0]
    >>> fanatic.actions.attack_form
    AnyMelee('The fanatic makes two melee attacks.')
    >>> {ac: fanatic.dpr(ac) for ac in (10, 15, 20)}
    {10: 6.75, 15: 4.5, 20: 2.25}
    """
    re = f'{re_name} makes {re_count(1)} melee attacks\.?'
    # we can select the most effective attacks from all melee options.
    # melee options seem to be consistently indicated with 'Melee' at the beginning of the action text.
    def _calc_dpr(self, target_ac, v):
        melee_attacks = [attack for attack in self.actions.attacks.values()
                         if attack['text'][:5].lower() == 'melee']
        return v.a1count * max(attack.dpr(target_ac) for attack in melee_attacks)
class AnyRanged(AttackForm):
    """MONSTER makes NUM ranged attacks."""
    re = f'{re_name} makes {re_count(1)} ranged attacks\.?'
    # we can select the most effective attacks from all ranged options
    # ranged options seem to be consistently indicated with 'Melee' at the beginning of the action text.
    def _calc_dpr(self, target_ac, v):
        ranged_attacks = [attack for attack in self.actions.attacks.values()
                         if attack['text'][:6].lower() == 'ranged']
        return v.a1count * max(attack.dpr(target_ac) for attack in ranged_attacks)
class MeleeOrRanged(AttackForm):
    """MONSTER makes NUM melee attacks or NUM ranged attacks.
    >>> from repltools import m
    >>> scout = m.where(name='Scout')[0]
    >>> scout.actions.attack_form
    MeleeOrRanged('The scout makes two melee attacks or two ranged attacks.')
    >>> {ac: scout.dpr(ac) for ac in (10, 15, 20)}
    {10: 9.75, 15: 6.5, 20: 3.25}
    """
    re = f'{re_name} makes {re_count(1)} melee attacks or {re_count(2)} ranged attacks\.?'
    # choose max of averages of optimal ranged and optimal melee attacks
    def _calc_dpr(self, target_ac, v):
        melee_attacks = [attack for attack in self.actions.attacks.values()
                         if attack['text'][:5].lower() == 'melee']
        ranged_attacks = [attack for attack in self.actions.attacks.values()
                         if attack['text'][:6].lower() == 'ranged']
        maxmelee = v.a1count * max([0] + [attack.dpr(target_ac) for attack in melee_attacks])
        maxranged = v.a2count * max([0] + [attack.dpr(target_ac) for attack in ranged_attacks])
        return max(maxmelee, maxranged)

class Named(AttackForm):
    """MONSTER makes NUM ATTACK attacks.

    >>> from repltools import m
    >>> liff = m.where(name='Lifferlas')[0]
    >>> liff.actions.attack_form
    Named('Lifferlas makes two slam attacks.')
    >>> {ac: liff.dpr(ac) for ac in (10, 15, 20)}
    {10: 24.65, 15: 17.4, 20: 10.15}
    """
    re = f'{re_name} makes {re_count(1)} {re_type_word(1)} attacks\.?'
    def _calc_dpr(self, target_ac, v):
        """Check if `type` matches an attack action name; otherwise fail."""
        return v.a1count * v.a1attack.dpr(target_ac)

class WithNamed(AttackForm):
    """MONSTER makes NUM attacks with ATTACK.

    >>> from repltools import m
    >>> displacer = m.where(name='Displacer Beast')[0]
    >>> displacer.actions.attack_form
    WithNamed('The displacer beast makes two attacks with its tentacles.')
    >>> {ac: displacer.dpr(ac) for ac in range(5, 30, 2)}
    {5: 14.25, 7: 14.25, 9: 13.5, 11: 12.0, 13: 10.5, 15: 9.0, 17: 7.5, 19: 6.0, 21: 4.5, 23: 3.0, 25: 1.5, 27: 0.75, 29: 0.75}
    """
    re = f'{re_name} makes {re_count(1)} (?:melee |ranged )?attacks with {re_article}{re_type_word(1)}\.'
    # same handler as 'named'
    _calc_dpr = Named._calc_dpr

class WithNamed2Options(AttackForm):
    """MONSTER makes TOTAL attacks with ATTACK1 or ATTACK2.

    >>> from repltools import m
    >>> urg = m.where(name='Urgala Meltimer')[0]
    >>> urg.actions.attack_form
    WithNamed2Options('Urgala makes two attacks with her morningstar or her shortbow.')
    >>> {ac: urg.dpr(ac) for ac in range(10, 25, 2)}
    {10: 12.0, 12: 10.5, 14: 9.0, 16: 7.5, 18: 6.0, 20: 4.5, 22: 3.0, 24: 1.5}
    """
    re = f'{re_name} makes {re_total} attacks with {re_article}{re_type_word(1)} or {re_article}{re_type_word(2)}\.'
    def _calc_dpr(self, target_ac, v):
        return v.total * max(v.a1attack.dpr(target_ac), v.a2attack.dpr(target_ac))

class NamedAndUses(AttackForm):
    """MONSTER makes NUM attack(s) with ATTACK and (uses|can use) ABILITY.

    >>> from repltools import m
    >>> devourer = m.where(name='Intellect Devourer')[0]
    >>> devourer.actions.attack_form
    NamedAndUses('The intellect devourer makes one attack with its claws and uses Devour Intellect.')
    >>> {ac: devourer.dpr(ac) for ac in range(12, 30, 2)}
    {12: 4.55, 14: 3.85, 16: 3.15, 18: 2.45, 20: 1.75, 22: 1.05, 24: 0.35, 26: 0.35, 28: 0.35}
    """
    re = f'{re_name} makes {re_count(1)} attacks? with {re_article}{re_type_word(1)} and (?:uses|can use) {re_article}\w+(?:\s\w+)' + r'{,3}\.?'
    dpr_confidence = '>'
    _calc_dpr = Named._calc_dpr # we ignore the "uses" clause.

class AttacksWithNamed(AttackForm):
    """MONSTER attacks [twice] with ATTACK.

    >>> from repltools import m
    >>> eblis = m.where(name='Eblis')[0]
    >>> eblis.actions.attack_form
    AttacksWithNamed('The eblis attacks twice with its beak.')
    >>> {ac: eblis.dpr(ac) for ac in range(0, 30, 2)}
    {0: 10.45, 2: 10.45, 4: 10.45, 6: 10.45, 8: 9.9, 10: 8.8, 12: 7.7, 14: 6.6, 16: 5.5, 18: 4.4, 20: 3.3, 22: 2.2, 24: 1.1, 26: 0.55, 28: 0.55}
    """
    re = f'{re_name} attacks ?(?P<num1>twice)? with {re_article}{re_type_word(1)}\.'
    def _calc_dpr(self, target_ac, v):
        return v.a1count * v.a1attack.dpr(target_ac)

class ArtAAndArtBOrC(AttackForm):
    """MONSTER makes TOTAL attacks: NUM1 with ATTACK1 and NUM2 with ATTACK2 or ATTACK3.

    >>> from repltools import m
    >>> slaad = m.where(name='Gray Slaad')[0]
    >>> slaad.actions.attack_form
    ArtAAndArtBOrC('The slaad makes three attacks: one with its bite and two with its claws or greatsword.')
    >>> {ac: slaad.dpr(ac) for ac in range(10, 29, 2)}
    {10: 23.85, 12: 21.2, 14: 18.55, 16: 15.9, 18: 13.25, 20: 10.6, 22: 7.95, 24: 5.3, 26: 2.65, 28: 1.325}
    """
    re = (f'{re_name} makes {re_total} attacks: '
          + f'{re_count(1)} with {re_article}{re_type_phrase(1)} '
          + f'and {re_count(2)} with {re_article}{re_type_phrase(2)} or {re_type_phrase(3)}\.')
    # similar to `a_and_art_b` but there's a choice between type2 and type3 for the second attack.
    def _calc_dpr(self, target_ac, v):
        dpr_one = v.a1count * v.a1attack.dpr(target_ac)
        dpr_two = v.a2count * max(v.a2attack.dpr(target_ac), v.a3attack.dpr(target_ac))
        return dpr_one + dpr_two

class ArtAAndArtB(AttackForm):
    """MONSTER makes TOTAL attacks: NUM1 with ATTACK1 and NUM2 with ATTACK2.

    >>> from repltools import m
    >>> bear = m.where(name='Brown Bear')[0]
    >>> bear.actions.attack_form
    ArtAAndArtB('The bear makes two attacks: one with its bite and one with its claws.')
    >>> {ac: bear.dpr(ac) for ac in (10, 15, 20)}
    {10: 16.575, 15: 11.7, 20: 6.825}

    >>> ghald = m.where(name='Ghald')[0]
    >>> ghald.actions.attack_form
    ArtAAndArtB('Ghald makes three attacks, one with his bite and two with his shortswords.')
    >>> {ac: ghald.dpr(ac) for ac in range(12, 27, 2)}
    {12: 24.8, 14: 21.7, 16: 18.6, 18: 15.5, 20: 12.4, 22: 9.3, 24: 6.2, 26: 3.1}
    """
    re = (f'{re_name} makes {re_total} (?:melee )?attacks[:,] '
          + f'{re_count(1)} with {re_article}{re_type_phrase(1)} '
          + f'and {re_count(2)} with {re_article}{re_type_phrase(2)}\.')
    def _calc_dpr(self, target_ac, v):
        """Sum of DPR from two different attacks."""
        return v.a1count * v.a1attack.dpr(target_ac) + v.a2count * v.a2attack.dpr(target_ac)
class TwiceArtAAndArtB(AttackForm):
    """MONSTER attacks twice, once with ATTACK1 and once with ATTACK2.

    >>> from repltools import m
    >>> drake = m.where(name='Black Guard Drake')[0]
    >>> drake.actions.attack_form
    TwiceArtAAndArtB('The drake attacks twice, once with its bite and once with its tail.')
    >>> {ac: drake.dpr(ac) for ac in range(12, 30, 2)}
    {12: 9.8, 14: 8.4, 16: 7.0, 18: 5.6, 20: 4.2, 22: 2.8, 24: 1.4, 26: 0.7, 28: 0.7}
    """
    re = f'{re_name} attacks (?P<total>twice)[,:] (?P<num1>once) with {re_article}{re_type_word(1)} and (?P<num2>once) with {re_article}{re_type_word(2)}\.?'
    _calc_dpr = ArtAAndArtB._calc_dpr

class MakesAAndB(AttackForm):
    """MONSTER makes NUM1 ATTACK1 and NUM2 ATTACK2 attack(s).

    >>> from repltools import m
    >>> norker = m.where(name='Norker')[0]
    >>> norker.actions.attack_form
    MakesAAndB('The norker makes one mace and one bite attack.')
    >>> {ac: norker.dpr(ac) for ac in range(12, 27, 2)}
    {12: 5.4, 14: 4.5, 16: 3.6, 18: 2.7, 20: 1.8, 22: 0.9, 24: 0.45, 26: 0.45}
    """
    re = f'{re_name} makes {re_count(1)} {re_type_word(1)} and {re_count(2)} {re_type_word(2)} attacks?\.'
    _calc_dpr = ArtAAndArtB._calc_dpr # we can reuse this since it doesn't look at `total` outside of validation

class AOrB(AttackForm):
    """MONSTER makes NUM1 ATTACK1 attacks or NUM2 ATTACK2 attacks.

    >>> from repltools import m
    >>> giant = m.where(name='Hundred-Handed One')[0]
    >>> giant.actions.attack_form
    AOrB('The giant makes four longsword attacks or two rock attacks.')
    >>> {ac: giant.dpr(ac) for ac in range(12, 27, 2)}
    {12: 81.7, 14: 81.7, 16: 77.4, 18: 68.8, 20: 60.2, 22: 51.6, 24: 43.0, 26: 34.4}
    """
    re = f'{re_name} makes {re_count(1)} {re_type_phrase(1)} attacks or {re_count(2)} {re_type_phrase(2)} attacks\.?'
    # check type1 & type2; fail if check fails; calculate optimal damage
    def _calc_dpr(self, target_ac, v):
        return max(v.a1count * v.a1attack.dpr(target_ac), v.a2count * v.a2attack.dpr(target_ac))

class NoMultiattack(AttackForm):
    """(Handles case where there is no multiattack string.)

    >>> from repltools import m
    >>> wolf = m.where(name='Wolf')[0]
    >>> wolf.actions.attack_form
    NoMultiattack(None)
    >>> {ac: wolf.dpr(ac) for ac in range(12, 27, 2)}
    {12: 4.55, 14: 3.85, 16: 3.15, 18: 2.45, 20: 1.75, 22: 1.05, 24: 0.35, 26: 0.35}
    """
    re = None
    def _validate(self):
        if self.actions.attacks:
            return Validated(attacks=self.actions.attacks)
        return None
    def _calc_dpr(self, target_ac, v):
        return max(attack.dpr(target_ac) for attack in v.attacks.values())

class ByHalfSpellLevel(AttackForm):
    """MONSTER makes a number of attacks equal to half this spell's level (rounded down).

    Assume the number of attacks is 1 for the purposes of calculating DPR.

    I think these always use your spell modifier for their attack bonus
    and thus cannot have their average DPR calculated automatically.

    >>> from repltools import m
    >>> celestial = m.where(name='Celestial Spirit')[0]
    >>> celestial.actions.attack_form
    ByHalfSpellLevel("The celestial makes a number of attacks equal to half this spell's level (rounded down).")
    >>> {ac: celestial.dpr(ac) for ac in range(12, 27, 2)}
    {12: 81.7, 14: 81.7, 16: 77.4, 18: 68.8, 20: 60.2, 22: 51.6, 24: 43.0, 26: 34.4}
    """
    re = f"{re_name} makes a number of attacks equal to half this spell's level \(rounded down\)\."
    dpr_confidence = '>='
    _validate = NoMultiattack._validate
    _calc_dpr = NoMultiattack._calc_dpr

class Default(AttackForm):
    """(Catch-all for whatever isn't matched by previous regexps.)

    This case catches a large number of exceptional cases.

    We don't know anything about multiattacks here so we just use the best attack.

    >>> from repltools import m
    >>> hobgoblin = m.where(name='Hobgoblin Iron Shadow')[0]
    >>> hobgoblin.actions.attack_form
    Default('The hobgoblin makes four attacks, each of which can be an unarmed strike or a dart attack. It can also use Shadow Jaunt once, either before or after one of the attacks.')
    >>> {ac: hobgoblin.dpr(ac) for ac in range(12, 27, 2)}
    {12: 3.85, 14: 3.3, 16: 2.75, 18: 2.2, 20: 1.65, 22: 1.1, 24: 0.55, 26: 0.275}
    """
    re = r'.*(?:\n.*)*'
    dpr_confidence = '>=~'
    _validate = NoMultiattack._validate
    _calc_dpr = NoMultiattack._calc_dpr
