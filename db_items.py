"""db_items

Contains Spell and Monster classes along with their base class and support functions.

Doctests for methods that don't get their doctests run for some reason:

>>> from dnd5edb.repltools import *
>>> aara = m.search('aara')[0]
>>> aara.dpr(15)
2.75
>>> aara.actions['Talon']['damage'] = '20'
>>> aara.dpr(15)
10.0
>>> big_bad_aara = deepcopy(aara)
>>> big_bad_aara.dpr(15)
10.0
>>> big_bad_aara.actions['Talon']['damage'] = '200'
>>> big_bad_aara.dpr(15)
100.0
>>> aara.dpr(15)
10.0
"""

from dnd5edb import parse, datatypes, calc
from dnd5edb.actions import Actions

def traverse_filter(item, predicate):
    """Traverses lists and dicts starting with `item`.

    Yields non-dict, non-list items for which predicate(item) returns True.

    >>> is_string = lambda v: type(v) is str
    >>> l = [1, 'two', 3, 'four']
    >>> list(traverse_filter(l, is_string))
    ['two', 'four']
    >>> dl = {1: 'one', 2: [2, 'two'], 3: [3, {"six": 4, 8: 'three'}]}
    >>> list(traverse_filter(dl, is_string))
    ['one', 'two', 'three']
    """
    if isinstance(item, dict):
        for subitem in item.values():
            yield from traverse_filter(subitem, predicate)
    elif isinstance(item, list):
        for subitem in item:
            yield from traverse_filter(subitem, predicate)
    elif predicate(item):
        yield item

class DBItem:
    """Abstract base class for Spell, Monster, and other database entries."""
    def fmt_xlist(self, tabstop=2):
        """Pointform output in xlist format.

        DBItem subclass must implement fmt_pointform for this to work.

        >>> from dnd5edb.collection import Spells, Monsters
        >>> print(Spells().search('Magic Missile')[0].fmt_xlist())
        * Magic Missile A/120'/I [V/S] (1:AArm+CA+S+Wz)
          " Evocation (PHB#257)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4 + 1 force damage to its target. The darts all strike simultaneously, and you can direct them to hit one creature or several.
          " At Higher Levels:
          " When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot level above 1st.
        >>> print(Monsters().search('Griffon')[0].fmt_xlist()) # doctest: +ELLIPSIS
        * Griffon: L UA monstrosity, 2.0CR DPR=16.6/11.7/6.8 59HP/7d10+21 12AC (walk 30, fly 80)
          " STR:18 DEX:15 CON:16 INT:2 WIS:13 CHA:8
          " skills: {'Perception': 5}
          " passive perception: 15
          " senses: {'darkvision': 60}
        ...
        """
        return self.fmt_pointform(header='*', body='"', tabstop=tabstop)

    def abbrev_sources(self):
        """Abbreviate the list of sources for this DB item."""
        return ', '.join(ref.abbr() for ref in self.sources)

    def _filter_fields(self, predicate):
        return traverse_filter(self.__dict__, predicate)

    def text_match(self, text):
        """Returns true if any of the item's text fields match `text`.

        >>> from dnd5edb.repltools import *
        >>> aara = m.where(name='Aarakocra')[0]
        >>> aara.text_match('asdfasdf')
        False
        >>> aara.text_match('aaqa')
        True
        >>> aara.text_match('summon')
        True
        >>> aara.text_match('melee weapon attack')
        True
        """
        def lc_match(term, field_text):
            return str(text).lower() in field_text.lower()
        is_string = lambda v: type(v) is str
        text_fields = self._filter_fields(is_string)
        return any(lc_match(text, field) for field in text_fields)

    def print(self, method='xlist', **kwargs):
        print(getattr(self, 'fmt_' + method)(**kwargs))

class Spell(DBItem):
    """Object with spell db object fields mapped as attributes."""
    char_classes = ["Artificer", "Bard", "Cleric", "Druid", "Fighter", "Monk",
                    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
                    "Eldritch Invocations", "Martial Adept", "Ritual Caster"]

    def __init__(self, node):
        self.__dict__.update(parse.SpellParser.parse(node))

    def __repr__(self):
        return f"Spell({self.fmt_oneline()})"

    @staticmethod
    def abbrev_class(char_class):
        """Abbreviate a given class name.

        >>> Spell.abbrev_class("Ranger")
        'Ra'
        >>> Spell.abbrev_class("Warlock")
        'Wl'
        >>> Spell.abbrev_class("Warlock (Great Old One)")
        'WlGOO'
        >>> Spell.abbrev_class("Rogue (Arcane Trickster)") # not actually used any more in the XML
        'RoAT'
        >>> Spell.abbrev_class("Fighter (Eldritch Knight)")
        'FEK'
        """
        return datatypes.caster_classes[char_class]
    
    def abbrev_time(spell):
        """Abbreviate time.

        Possible return values: A, R, 1m, C1h, etc.
        """
        return spell.time.abbr()

    def abbrev_range(spell):
        """Abbreviate range.

        Possible return values: 10', 120', 500mi, S, S(30'cone), Unlimited, etc
        """
        return spell.range.abbr()

    def abbrev_duration(spell):
        """Abbreviate spell duration.

        Some possible return values:
        N (none), S (special), 1r (1 round), 1m, 1h, <=1h, C1h (1h concentration)
        """
        c = 'C' if spell.concentration else ''
        return c + spell.duration.abbr()

    def abbrev_components(spell):
        """Abbreviate spell components."""
        components = []
        for c in spell.components:
            if c in ['V', 'S', 'R']:
                components += [c]
            if c == 'M':
                monetary = []
                if 'used' in spell.components:
                    monetary += [f'{spell.components["used"]}']
                if 'consumed' in spell.components:
                    monetary += [f'!{spell.components["consumed"]}!']

                if monetary:
                    components += [f'M@{"+".join(monetary)}gp']
                else:
                    components += ['M']
        return '[' + '/'.join(components) + ']'

    def abbrev_classes(spell):
        """Abbreviate the classes which have access to a given spell.

        Return values are those from abbrev_class, joined with '+'.
        """
        return '+'.join(Spell.abbrev_class(c) for c in spell.classes)


    def fmt_oneline(self):
        """Return a string summarizing the spell.

        Format:
            NAME T/R/D [C] (L:CLASSES)

        Where
            T = Time
            R = Range
            D = Duration
            C = Components
            L = Level

        >>> from dnd5edb.collection import Spells
        >>> test = lambda name: Spells().search(name)[0].fmt_oneline()
        >>> test('Banishing Smite')
        'Banishing Smite B/S/C<=1m [V] (5:ABS+P+WlH)'

        Minimum value of material components is shown with "@___gp" after the "M"
        >>> test('Identify')
        'Identify (rit.) 1m/T/I [V/S/M@100gp] (1:A+Bd+CF+CK+Wz)'

        *Consumed* material component values are surrounded by exclamation points
        >>> test('Revivify')
        'Revivify A/T/I [V/S/M@!300!gp] (3:A+C+CG+CLf+D+DW+P+Ra+WlC)'

        Some spells have both consumed and non-consumed components with monetary value
        >>> test('Clone')
        'Clone 1h/T/I [V/S/M@2000+!1000!gp] (8:Wz)'
        """
        f = self._abbrev_fields()
        return "{name}{rit} {t}/{r}/{d} {c} ({l}:{classes})".format(**f)

    def _abbrev_fields(self):
        """Returns dict with field names and abbreviations of their values.

        Used by fmt_oneline and other formatting functions.
        """
        return {
            'name': self.name,
            'rit': ' (rit.)' if self.ritual else '',
            't': self.abbrev_time(),
            'r': self.abbrev_range(),
            'd': self.abbrev_duration(),
            'c': self.abbrev_components(),
            'l': self.level,
            'classes': self.abbrev_classes()}

    def fmt_pointform(spell, header='-', body='-', tabstop=2):
        """Return multiline string containing all spell information.

        The top line is a one-line header via self.fmt_oneline.
        The second, and first indented, line contains the spell school and sourcebook references.
        If there are material components, they are also shown on the second line.
        The remaining lines are the spell text.
        `header` and `body` are single-character bullets
            used for their respective types of lines.
        `tabstop` determines the depth to which the body lines are indented.

        By default, uses `-` as the bullet for all lines and tabstop of 2:
        >>> from dnd5edb.collection import Spells
        >>> print(Spells().search('Magic Missile')[0].fmt_pointform())
        - Magic Missile A/120'/I [V/S] (1:AArm+CA+S+Wz)
          - Evocation (PHB#257)
          - You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4 + 1 force damage to its target. The darts all strike simultaneously, and you can direct them to hit one creature or several.
          - At Higher Levels:
          - When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot level above 1st.

        Tabstop can be customized:
        >>> print(Spells().search('Magic Missile')[0].fmt_pointform(tabstop=4))
        - Magic Missile A/120'/I [V/S] (1:AArm+CA+S+Wz)
            - Evocation (PHB#257)
            - You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4 + 1 force damage to its target. The darts all strike simultaneously, and you can direct them to hit one creature or several.
            - At Higher Levels:
            - When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot level above 1st.

        Bullet can be set separately for the header and body lines:
        >>> print(Spells().search('Magic Missile')[0].fmt_pointform(header='*', body='"'))
        * Magic Missile A/120'/I [V/S] (1:AArm+CA+S+Wz)
          " Evocation (PHB#257)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4 + 1 force damage to its target. The darts all strike simultaneously, and you can direct them to hit one creature or several.
          " At Higher Levels:
          " When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot level above 1st.

        If the spell has material components, these are listed on a separate line above the spell text:
        >>> print(Spells().search('identify')[0].fmt_pointform())
        - Identify (rit.) 1m/T/I [V/S/M@100gp] (1:A+Bd+CF+CK+Wz)
          - Divination (PHB#252); Material components: a pearl worth at least 100 gp and an owl feather
          - You choose one object that you must touch throughout the casting of the spell. If it is a magic item or some other magic-imbued object, you learn its properties and how to use them, whether it requires attunement to use, and how many charges it has, if any. You learn whether any spells are affecting the item and what they are. If the item was created by a spell, you learn which spell created it.
          - If you instead touch a creature throughout the casting, you learn what spells, if any, are currently affecting it.

        If a spell has multiple sources, they are all listed:
        >>> Spells().search('Wall of Water').print('xlist')
        * Wall of Water A/60'/C<=10m [V/S/M] (3:D+S+Wz)
          " Evocation (XGtE#170, EEPC#23, VGM#116, MOoT); Material components: a drop of water
          " You create a wall of water on the ground at a point you can see within range. You can make the wall up to 30 feet long, 10 feet high, and 1 foot thick, or you can make a ringed wall up to 20 feet in diameter, 20 feet high, and 1 foot thick. The wall vanishes when the spell ends. The wall's space is difficult terrain.
          " Any ranged weapon attack that enters the wall's space has disadvantage on the attack roll, and fire damage is halved if the fire effect passes through the wall to reach its target. Spells that deal cold damage that pass through the wall cause the area of the wall they pass through to freeze solid (at least a 5-foot-square section is frozen). Each 5-foot-square frozen section has AC 5 and 15 hit points. Reducing a frozen section to 0 hit points destroys it. When a section is destroyed, the wall's water doesn't fill it.
        """
        ret = [f'{header} {spell.fmt_oneline()}']
        linetwo = f'{" " * tabstop}{body} {spell.school} ({spell.abbrev_sources()})'
        material = spell.components.get('M', '')
        if material:
            linetwo += f'; Material components: {material}'
        ret += [linetwo]
        ret += [f'{" " * tabstop}{body} {line}' for line in spell.text.split('\n')]
        return '\n'.join(ret)

    def fmt_plop(self):
        """Output in a format useful for plugging into Tableplop VTT."""
        f = self._abbrev_fields()
        ret = ["{t}: {name}{rit} {t}/{r}/{d} (L{l})".format(**f)]
        ret += ["{name}: range: {r}, duration: {d}; level {l}".format(**f)]
        ret += self.text.split("\n")
        ret = "\n".join(line for line in ret if line.strip() != '')
        return ret

    def subclass_set(spell, class_):
        """Returns a terse indicator of which subclasses of `class` get the spell.

        Returns '*' if all do
        Returns '-' if none do
        Returns eg 'CO+CLf' if Order and Life clerics get the spell.
        """
        if class_ in spell.classes:
            return '*'
        else:
            subclasses = [c for c in spell.classes
                          if c.startswith(class_)]
            if subclasses:
                return '+'.join(Spell.abbrev_class(c) for c in subclasses)
            else:
                return '-'

    def summary_class_columns(spell, classes=char_classes):
        """ Return a line summarizing the spell with a column for each class.

        Uses CSV format and column set compatible with Spells.csv_table().
        """
        components = [spell.name,
                      spell.abbrev_time(),
                      spell.abbrev_range(),
                      spell.abbrev_duration(),
                      str(spell.level) ]
        components += [spell.subclass_set(c) for c in classes]

        return ', '.join(components)

class Monster(DBItem):
    def __init__(self, node=None, **kwargs):
        """Instantiates this instance using data from the XML `node` or custom data.

        Custom data (passed via keyword arguments) is typically used
        to enter PC AC, HP, attacks, etc. for use in encounter balancing.

        >>> from dnd5edb.collection import Spells, Monsters
        >>> l3rogue = Monster(ac_num=16, hp=30, actions={'Crossbow': {'attack_bonus': 6, 'damage': '1d8+3+2d6'}})
        >>> party = Monsters([l3rogue])
        >>> party.combat_stats(12) # combat effectiveness vs 12 AC
        {'dpr': 10.9, 'avg_ac': 16.0, 'weighted_ac': 16.0, 'hp': 30}
        """
        if node is not None:
            self.__dict__.update(parse.MonsterParser.parse(node))
        else:
            self.__dict__.update(kwargs)
            if hasattr(self, 'actions'):
                self.actions = Actions(self.actions)

    def __repr__(self):
        return f"Monster({self.fmt_oneline()})"

    def fmt_oneline(self):
        """Returns a one-line summary of the item.

        >>> from dnd5edb.collection import Spells, Monsters
        >>> Monsters().where(name='Giant Crab')[0].fmt_oneline()
        'Giant Crab: M UA beast, 1/8CR DPR=3.1/2.0/0.9 13HP/3d8 15AC (walk 30, swim 30)'
        >>> Monsters().where(name='Crab Folk')[0].fmt_oneline()
        'Crab Folk: L TN giant, 3.0CR DPR=12.8/9.0/5.2 68HP/8d10+24 16AC (walk 40, swim 40)'
        """
        fmt = '{name}: {size} {alignment} {type}, {cr}CR {dpr} {hp}HP/{hitdice} {ac_num}AC ({speeds})'

        fields = ['name', 'size', 'alignment', 'type', 'hp', 'hitdice', 'ac_num', 'dpr']
        # fill `fields` from attributes of `self`
        fields = {field: getattr(self, field, '--') for field in fields}

        align_abbrevs = {'Lawful Good'    : 'LG'  , 'Neutral Good' : 'NG' , 'Chaotic Good'    : 'CG' ,
                         'Lawful Neutral' : 'LN'  , 'Neutral'      : 'TN' , 'Chaotic Neutral' : 'CN' ,
                         'Lawful Evil'    : 'LE'  , 'Neutral Evil' : 'NE' , 'Chaotic Evil'    : 'CE' ,
                         'Unaligned'      : 'UA'}
        fields = {key: align_abbrevs[value] if key == 'alignment' and value in align_abbrevs else value
                  for key, value in fields.items()}

        cr_table = {0.125: '1/8', 0.25: '1/4', 0.5: '1/2'}
        cr = getattr(self, 'cr', None)
        fields['cr'] = '--' if cr is None else cr_table[cr] if cr % 1 else str(cr)

        speed = getattr(self, 'speed', {'NO': 'MOVEMENT'})
        fields['speeds'] = ', '.join(' '.join([mode, str(dist)]) for mode, dist in speed.items())

        if hasattr(self, 'actions') and self.actions.attacks:
            process_dpr = lambda dpr: '??' if dpr is None else str(round(dpr, 1))
            dpr_spread = [process_dpr(self.dpr(ac)) for ac in (10, 15, 20)]
            dpr_operator = self.actions.attack_form.dpr_confidence
            dpr_text = f'DPR{dpr_operator}{"/".join(dpr_spread)}'
        else:
            dpr_text = 'DPR:??'
            # many creatures have attack actions which do not include the attack bonus and damage elements.
        fields['dpr'] = dpr_text

        # inject the fields from `self` into the format string
        return fmt.format(**fields)

    def fmt_full(self):
        def render_text(name=None, alignment=None, type=None,
                        size=None, cr=None, hp=None, hitdice=None,
                        ac=None, ac_num=None, speed=None,
                        str=None, dex=None, con=None,
                        int=None, wis=None, cha=None,
                        skills=None, saves=None,
                        passive=None, senses=None, senses_notes=None,
                        spells=None, slots=None, armor=None,
                        immune=None, immune_notes=None,
                        resist=None, resist_notes=None,
                        conditionImmune=None, conditionImmune_notes=None,
                        vulnerable=None, description=None, actions=None):
            text = []

            text.append(f'{name} ({alignment} {type})  Size: {size}  CR: {cr}')

            text.append(f'HP: {hp}({hitdice})  AC: {ac}({ac_num})  Speed: {speed}')

            text.append(f'STR:{str} DEX:{dex} CON:{con} INT:{int} WIS:{wis} CHA:{cha}')

            if skills:
                text.append(f'skills: {skills}')
            if saves:
                text.append(f'saves: {saves}')
            text.append(f'passive perception: {passive}')
            if senses:
                text.append(f'senses: {senses}')
                if senses_notes:
                    text.append(f'NOTE: {senses_notes}')

            if spells:
                text.append(f'spells: {spells}')
            if slots:
                text.append(f'slots: {slots}')

            if armor:
                text.append(f'armor: {armor}')

            if immune:
                text.append(f'immunities: {immune}')
                if immune_notes:
                    text.append(f'NOTE: {immune_notes}')
            if resist:
                text.append(f'resistances: {resist}')
                if resist_notes:
                    text.append(f'NOTE: {resist_notes}')
            if conditionImmune:
                text.append(f'condition immunities: {conditionImmune}')
                if conditionImmune_notes:
                    text.append(f'NOTE: {conditionImmune_notes}')
            if vulnerable:
                text.append(f'vulnerabilities: {vulnerable}')

            # * 'description': 255,
            if description:
                text.append(description)

            if actions:
                text.append('ACTIONS:')
                for name, details in actions.items():
                    text.append(f'{name}: {details.get("text", "")}')

            return '\n'.join(text)

        fields = ['name', 'alignment', 'type', 'size', 'cr',
                  'hp', 'hitdice', 'ac', 'ac_num', 'speed',
                  'str', 'dex', 'con', 'int', 'wis', 'cha',
                  'skills', 'saves', 'passive', 'senses', 'senses_notes',
                  'spells', 'slots', 'armor', 'immune', 'immune_notes',
                  'resist', 'resist_notes',
                  'conditionImmune', 'conditionImmune_notes',
                  'vulnerable', 'description', 'actions']

        fields = dict((f, getattr(self, f, None)) for f in dir(self) if f in fields)
        return render_text(**fields)

    def fmt_pointform(self, header='-', body='-', tabstop=2):
        """Multiline string containing point-form summary of item.

        Similar to `Spell.fmt_pointform`.

        First line is simply output of `self.fmt_oneline()`.
        Subsequent lines are any remaining lines after the first two
        in the output of `self.fmt_full()`.

        >>> from dnd5edb.collection import Spells, Monsters
        >>> Monsters().where(name='Goblin').print('pointform') # doctest: +ELLIPSIS
        - Goblin: S NE humanoid (goblinoid), 1/4CR DPR=4.1/2.8/1.4 7HP/2d6 15AC (walk 30)
          - STR:8 DEX:14 CON:10 INT:10 WIS:8 CHA:8
          - skills: {'Stealth': 6}
          - passive perception: 9
          - senses: {'darkvision': 60}
          - armor: leather armor, shield
        ...
        """
        ret = [f'{header} {self.fmt_oneline()}']
        ret += [f'{" " * tabstop}{body} {line}' for line in self.fmt_full().split('\n')[2:]]
        return '\n'.join(ret)

    @property
    def dpr(self):
        """Overly complicated way of caching dpr method.  I have no idea why I wrote it this way."""
        if hasattr(self, 'actions'):
            return lambda *args, **kwargs: calc.round4(self.actions.dpr(*args, **kwargs))
        else:
            return lambda *args, **kwargs: None
