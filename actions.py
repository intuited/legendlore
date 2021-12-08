"""Handle actions, in particular, attack actions.
"""
import re
from dnd5edb import calc
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

    @property
    def attacks(self):
        """Subset of Actions which have `attack_bonus` and `damage` entries."""
        return {name: Attack(attack) for name, attack in self.items()
                if 'attack_bonus' in attack and 'damage' in attack}

    @property
    def multiattack_text(self):
        try:
            return self['Multiattack']['text']
        except KeyError:
            return None

    @property
    def attack_form(self):
        """Matches multiattack text to one of the REs in attack_forms.keys().

        Returns an instantiated object of the class keyed by that RE.
        """
        return AttackForm(self)

class Attack(dict):
    def dpr(self, target_ac):
        if 'attack_bonus' in self and 'damage' in self:
            return calc.dpr(target_ac, self['attack_bonus'], self['damage'])
        return None

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
    dpr_confidence='='

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
            if attack_name.lower() == 'hooves':
                if name.lower() == 'hoof':
                    return attack
            if attack_name.lower() == 'adamantine greatclub':
                if name.lower() == 'greatclub':
                    return attack
            if attack_name[:3] == '+1 ':
                if name.lower() == attack_name[3:].lower() + ' +1':
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
        w = lambda m: warning(f'{self.__class__.__name__}._validate: {m}.  MA string: "{getattr(self.match, "string", None)}"')
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
re_words = lambda n: r'\w+(?:\s\w+){,' + str(n-1) + '}'

#### Handlers: these are subclasses of AttackForm which override `re` and `_calc_dpr`, as well as possibly `_validate`.
# Note that each time a class subclasses AttackForm, it's added to the sequential list of handlers.

### Custom handlers first: these catch specific strings that would otherwise be false positives for generic handlers.
# These typically override `dpr` rather than `_calc_dpr`, as there is no validation for them to do.
class Centaur(AttackForm):
    """Centaur.

    >>> from dnd5edb.repltools import m
    >>> {ac: m.where(name='Centaur')[0].dpr(ac) for ac in range(10, 31, 2)}
    {10: 17.425, 12: 15.375, 14: 13.325, 16: 11.275, 18: 9.225, 20: 7.175, 22: 5.125, 24: 3.075, 26: 1.025, 28: 1.025, 30: 1.025}
    """
    re = 'The centaur makes two attacks: one with its pike and one with its hooves or two with its longbow\.'
    def dpr(self, target_ac):
        return max(self._match_attack('Pike').dpr(target_ac) + self._match_attack('Hooves').dpr(target_ac),
                   2 * self._match_attack('Longbow').dpr(target_ac))
class Lamia(AttackForm):
    re = "The lamia makes two attacks: one with its claws and one with its dagger or Intoxicating Touch\."
    def dpr(self, target_ac):
        return self._match_attack('Claws').dpr(target_ac) + self._match_attack('Dagger').dpr(target_ac)
class Manticore(AttackForm):
    re = "The manticore makes three attacks: one with its bite and two with its claws or three with its tail spikes."
    def dpr(self, target_ac):
        return max(self._match_attack('Bite').dpr(target_ac) + 2 * self._match_attack('Claws').dpr(target_ac),
                   self._match_attack('Tail Spikes').dpr(target_ac))
class Orc(AttackForm):
    """The Orc War Chief's Greataxe attack doesn't provide an attack handler or damage bonus.

    >>> from repltools import m
    >>> orc = m.where(name='Orc War Chief')[0]
    >>> orc.actions.attack_form
    Orc('The orc makes two attacks with its greataxe or its spear.')
    >>> {ac: orc.dpr(ac) for ac in range(12, 27, 2)}
    {12: 22.5, 14: 19.5, 16: 16.5, 18: 13.5, 20: 10.5, 22: 7.5, 24: 4.5, 26: 1.5}

    Should equal the following:
    >>> {ac: calc.round4(2*calc.dpr(ac, 6, '1d12+4+1d8')) for ac in range(12, 27, 2)}
    {12: 22.5, 14: 19.5, 16: 16.5, 18: 13.5, 20: 10.5, 22: 7.5, 24: 4.5, 26: 1.5}
    """
    re = "The orc makes two attacks with its greataxe or its spear."
    def dpr(self, target_ac):
        return 2 * max(self._match_attack('Spear').dpr(target_ac),
                       calc.dpr(target_ac, 6, '1d12+4+1d8'))

class Devil(AttackForm):
    """These and/or forms are ambiguous because without doing some counting we don't know the operator precedence.

    I.E. "A and B or C" could mean "(A and B) or C" or "A and (B or C)".

    There's only like 4 of them so we might as well just write custom handlers for them.

    >>> from repltools import m
    >>> devil = m.where(name='Spined Devil')[0]
    >>> devil.actions.attack_form
    Devil('The devil makes two attacks: one with its bite and one with its fork or two with its tail spines.')
    >>> {ac: devil.dpr(ac) for ac in range(10, 29, 2)}
    {10: 6.75, 12: 5.85, 14: 4.95, 16: 4.05, 18: 3.15, 20: 2.25, 22: 1.35, 24: 0.45, 26: 0.45, 28: 0.45}
    """
    re = "The devil makes two attacks: one with its bite and one with its fork or two with its tail spines\."
    def dpr(self, target_ac):
        return max(self._match_attack('Bite').dpr(target_ac) + self._match_attack('Fork').dpr(target_ac),
                   2 * self._match_attack('Tail Spine').dpr(target_ac))
class Morkoth(AttackForm):
    """Another form ambiguous for similar reasons.

    >>> from repltools import m
    >>> devil = m.where(name='Morkoth')[0]
    >>> devil.actions.attack_form
    Morkoth('The morkoth makes three attacks: two with its bite and one with its tentacles or three with its bite.')
    >>> {ac: devil.dpr(ac) for ac in range(10, 29, 2)}
    {10: 28.475, 12: 25.125, 14: 21.775, 16: 18.425, 18: 15.075, 20: 11.725, 22: 8.375, 24: 5.025, 26: 1.675, 28: 1.675}
    """
    re = 'The morkoth makes three attacks: two with its bite and one with its tentacles or three with its bite.'
    def dpr(self, target_ac):
        dpr_one = 2 * self._match_attack('Bite').dpr(target_ac) + self._match_attack('Tentacles').dpr(target_ac)
        dpr_two = 3 * self._match_attack('Bite').dpr(target_ac)
        return max(dpr_one, dpr_two)

class Marut(AttackForm):
    """'Slam' attack refers to its "Unerring Slam", which auto-hits for 60 force damage.

    >>> from repltools import m
    >>> marut = m.where(name='Marut')[0]
    >>> marut.actions.attack_form
    Marut('The marut makes two slam attacks.')
    >>> {ac: marut.dpr(ac) for ac in range(10, 29, 2)}
    {10: 120, 12: 120, 14: 120, 16: 120, 18: 120, 20: 120, 22: 120, 24: 120, 26: 120, 28: 120}
    """
    re = 'The marut makes two slam attacks\.'
    def dpr(self, target_ac):
        return 120
class Hunter(AttackForm):
    re = "The blood hunter attacks twice with a weapon\."
    def dpr(self, target_ac):
        return 2 * max(self._match_attack('Greatsword').dpr(target_ac), self._match_attack('Heavy Crossbow').dpr(target_ac))
class Sansuri(AttackForm):
    """Multiattack references a spear attack she doesn't seem to have.

    Just using the basic attacks.
    """
    re = 'Sansuri makes two spear attacks\.'
    def dpr(self, target_ac):
        return max(attack.dpr(target_ac) for attack in self.actions.attacks.values())
class Generator(AttackForm):
    """Uses an autohit dart attack.

    >>> from repltools import m
    >>> generator = m.where(name='Play-by-Play Generator')[0]
    >>> generator.actions.attack_form
    Generator('The generator makes two fist attacks or four dart attacks.')
    >>> {ac: generator.dpr(ac) for ac in range(6, 29, 4)}
    {6: 20.0, 10: 20.0, 14: 20.0, 18: 20.0, 22: 20.0, 26: 20.0}
    """
    re = 'The generator makes two fist attacks or four dart attacks\.'
    def dpr(self, target_ac):
        dpr_fist = 2 * self._match_attack('Fist').dpr(target_ac)
        dpr_dart = 4 * calc.avg('2d4')
        return max(dpr_fist, dpr_dart)
class Stomper(AttackForm):
    """We don't handle this one because it requires a saving throw for its multiattack.

    >>> from repltools import m
    >>> stomper = m.where(name='Shockerstomper')[0]
    >>> stomper
    Monster(Shockerstomper: G UA construct, 14.0CR DPR=??/??/?? 300HP/300d1 18AC (walk 40))
    >>> stomper.actions.attack_form
    Stomper('Shockerstomper makes three Lightning Turret attacks and two Stomp attacks.')
    >>> {ac: stomper.dpr(ac) for ac in range(6, 29, 4)}
    {6: None, 10: None, 14: None, 18: None, 22: None, 26: None}
    """
    re = 'Shockerstomper makes three Lightning Turret attacks and two Stomp attacks.'
    def dpr(self, target_ac):
        return None

### Generic handlers: use broadly constructed regexps to identify classes of multiattack strings.

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
    re = f'{re_name} makes {re_total} (?:weapon )?attacks\.?'
    # we can select the most effective attacks from all options
    def _calc_dpr(self, target_ac, v):
        return v.total * max(attack.dpr(target_ac) for attack in self.actions.attacks.values())
class NumWithWeapon(AttackForm):
    """MONSTER attacks NUM with a weapon.

    This is just a rewording of the above case: we are ignoring unarmed strikes, at least for now.

    >>> from repltools import m
    >>> sephek = m.where(name='Sephek Kaltro')[0]
    >>> sephek.actions.attack_form
    NumWithWeapon('Sephek attacks twice with a weapon.')
    >>> {ac: sephek.dpr(ac) for ac in range(10, 31, 2)}
    {10: 12.0, 12: 10.5, 14: 9.0, 16: 7.5, 18: 6.0, 20: 4.5, 22: 3.0, 24: 1.5, 26: 0.75, 28: 0.75, 30: 0.75}
    """
    re = f'{re_name} attacks {re_total} with a weapon\.?'
    _calc_dpr = Any._calc_dpr

class AnyMelee(AttackForm):
    """MONSTER makes NUM melee attacks.

    >>> from repltools import m
    >>> fanatic = m.where(name='Cult Fanatic')[0]
    >>> fanatic.actions.attack_form
    AnyMelee('The fanatic makes two melee attacks.')
    >>> {ac: fanatic.dpr(ac) for ac in (10, 15, 20)}
    {10: 6.75, 15: 4.5, 20: 2.25}
    """
    re = f'{re_name} makes {re_count(1)} melee (?:weapon )?attacks\.?'
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

class NumAAndNumBOrC(AttackForm):
    """MONSTER makes TOTAL attacks: NUM1 with its ATTACK1 and NUM2 with its ATTACK2 or ATTACK3.

    >>> from repltools import m
    >>> slaad = m.where(name='Gray Slaad')[0]
    >>> slaad.actions.attack_form
    NumAAndNumBOrC('The slaad makes three attacks: one with its bite and two with its claws or greatsword.')
    >>> {ac: slaad.dpr(ac) for ac in range(10, 29, 2)}
    {10: 23.85, 12: 21.2, 14: 18.55, 16: 15.9, 18: 13.25, 20: 10.6, 22: 7.95, 24: 5.3, 26: 2.65, 28: 1.325}
    """
    re = (f'{re_name} makes {re_total} (?:melee )?attacks: '
          + f'{re_count(1)} with {re_article}{re_type_phrase(1)} '
          + f'and {re_count(2)} with (?:either )?{re_article}{re_type_phrase(2)} or {re_article}{re_type_phrase(3)}\.')
    # similar to `a_and_art_b` but there's a choice between type2 and type3 for the second attack.
    def _calc_dpr(self, target_ac, v):
        dpr_one = v.a1count * v.a1attack.dpr(target_ac)
        dpr_two = v.a2count * max(v.a2attack.dpr(target_ac), v.a3attack.dpr(target_ac))
        return dpr_one + dpr_two

class NumArtAorArtBAndNumArtC(AttackForm):
    """MONSTER makes TOTAL attacks: NUM1 with its ATTACK1 or ATTACK2 and NUM2 with its ATTACK3.

    >>> from repltools import m
    >>> canoloth = m.where(name='Canoloth')[0]
    >>> canoloth.actions.attack_form
    NumArtAorArtBAndNumArtC('The canoloth makes two attacks: one with its tongue or its bite and one with its claws.')
    >>> {ac: canoloth.dpr(ac) for ac in (10, 15, 20)}
    {10: 36.0, 15: 26.0, 20: 16.0}
    """
    re = (f'{re_name} makes {re_total} attacks: {re_count(1)} '
          + f'with {re_article}{re_type_word(1)} or {re_article}{re_type_word(2)} '
          + f'and {re_count(3)} with {re_article}{re_type_word(3)}\.')
    def _calc_dpr(self, target_ac, v):
        dpr_one = v.a1count * max(v.a1attack.dpr(target_ac), v.a2attack.dpr(target_ac))
        dpr_two = v.a3count * v.a3attack.dpr(target_ac)
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

class MakesAAttackAndBAttack(AttackForm):
    """MONSTER makes NUM1 ATTACK1 and NUM2 ATTACK2 attack(s).

    >>> from repltools import m
    >>> peryton = m.where(name='Peryton')[0]
    >>> peryton.actions.attack_form
    MakesAAttackAndBAttack('The peryton makes one gore attack and one talon attack.')
    >>> {ac: peryton.dpr(ac) for ac in range(12, 27, 2)}
    {12: 10.85, 14: 9.3, 16: 7.75, 18: 6.2, 20: 4.65, 22: 3.1, 24: 1.55, 26: 0.775}
    """
    re = f'{re_name} makes {re_count(1)} {re_type_word(1)} attacks? and {re_count(2)} {re_type_word(2)} attacks?\.'
    _calc_dpr = ArtAAndArtB._calc_dpr # we can reuse this since it doesn't look at `total` outside of validation

class MakesAAndBAttack(AttackForm):
    """MONSTER makes NUM1 ATTACK1 and NUM2 ATTACK2 attack(s).

    >>> from repltools import m
    >>> norker = m.where(name='Norker')[0]
    >>> norker.actions.attack_form
    MakesAAndBAttack('The norker makes one mace and one bite attack.')
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
    {12: None, 14: None, 16: None, 18: None, 20: None, 22: None, 24: None, 26: None}
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
