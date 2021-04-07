from functools import partial
from dnd5edb import parse, predicates, reflect

class DBItem:
    """Abstract base class for Spell, Monster, and other database entries."""
    def fmt_xlist(self, tabstop=2):
        """Pointform output in xlist format.

        DBItem subclass must implement fmt_pointform for this to work.

        >>> print(Spells().search('Magic Missile')[0].fmt_xlist())
        * Magic Missile A/120'/I (1:FEK+S+Wz)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
          " 
          " At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.
        >>> print(Monsters().search('Griffon')[0].fmt_xlist())
        * Griffon: L unaligned monstrosity, 2.0CR 59HP/7d10+21 12AC (walk 30, fly 80)
          " STR:18 DEX:15 CON:16 INT:2 WIS:13 CHA:8
          " skills: {'Perception': 5}
          " passive perception: 15
          " senses: {'darkvision': 60}
        """
        return self.fmt_pointform(header='*', body='"', tabstop=tabstop)


class Spell(DBItem):
    """Object with spell db object fields mapped as attributes."""
    schools = {'EV': "Evocation",
               'T': "Transmutation",
               'C': "Conjuration",
               'A': "Abjuration",
               'EN': "Enchantment",
               'D': "Divination",
               'N': "Necromancy",
               'I': "Illusion",
               None: None}

    char_classes = ["Artificer", "Bard", "Cleric", "Druid", "Fighter", "Monk",
                    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
                    "Eldritch Invocations", "Martial Adept", "Ritual Caster"]

    def __init__(self, node):
        self.__dict__.update(parse.Spell.parse(node))

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
        'WlG'
        >>> Spell.abbrev_class("Rogue (Arcane Trickster)")
        'AT'
        >>> Spell.abbrev_class("Fighter (Eldritch Knight)")
        'FEK'
        """
        abbr = {'Artificer': "A",
                'Bard': "B",
                'Cleric (Arcana)': "CA",
                'Cleric (Death)': "CD",
                'Cleric (Forge)': "CF",
                'Cleric (Grave)': "CG",
                'Cleric (Knowledge)': "CK",
                'Cleric (Life)': "CLf",
                'Cleric (Light)': "CLt",
                'Cleric (Nature)': "CN",
                'Cleric (Order)': "CO",
                'Cleric (Protection)': "CP",
                'Cleric (Tempest)': "CTm",
                'Cleric (Trickery)': "CTr",
                'Cleric (War)': "CW",
                'Cleric': "C",
                'Druid (Arctic)': "DA",
                'Druid (Coast)': "DC",
                'Druid (Desert)': "DD",
                'Druid (Forest)': "DF",
                'Druid (Grassland)': "DG",
                'Druid (Mountain)': "DM",
                'Druid (Swamp)': "DS",
                'Druid (Underdark)': "DU",
                'Druid': "D",
                'Eldritch Invocations': "EI",
                'Fighter': "F",
                'Fighter (Arcane Archer)': "FAA",
                'Fighter (Battle Master)': "FBM",
                'Fighter (Eldritch Knight)': "FEK",
                'Martial Adept': "MA",
                'Monk': "M",
                'Monk (Way of the Four Elements)': "M4",
                'Paladin (Ancients)': "PA",
                'Paladin (Conquest)': "PCn",
                'Paladin (Crown)': "PCr",
                'Paladin (Devotion)': "PD",
                'Paladin (Oathbreaker)': "PO",
                'Paladin (Redemption)': "PR",
                'Paladin (Treachery)': "PT",
                'Paladin (Vengeance)': "PV",
                'Paladin': "P",
                'Ranger (Gloom Stalker)': "RGS",
                'Ranger (Horizon Walker)': "RHW",
                'Ranger (Monster Slayer)': "RMS",
                'Ranger (No Spells)': "R",
                'Ranger (Primeval Guardian)': "RPG",
                'Ranger': "Ra",
                'Ritual Caster': "Rit",
                'Rogue': "Ro",
                'Rogue (Arcane Trickster)': "AT",
                'Sorcerer (Stone Sorcery)': "SSS",
                'Sorcerer': "S",
                'Warlock (Archfey)': "WlA",
                'Warlock (Celestial)': "WlC",
                'Warlock (Fiend)': "WlF",
                'Warlock (Great Old One)': "WlG",
                'Warlock (Hexblade)': "WlH",
                'Warlock (Raven Queen)': "WlR",
                'Warlock (Seeker)': "WlS",
                'Warlock (Undying)': "WlU",
                'Warlock': "Wl",
                'Wizard': "Wz"}

        return abbr[char_class]
    
    def abbrev_time(spell):
        """Abbreviate time.

        Possible return values: A, R, 1m, C1h, etc.
        """
        abbr = {None: 'N',
                'None': 'N',
                '1 action': 'A',
                'part of the Attack action to fire a magic arrow': 'A*',
                '1 bonus action': 'B',
                '1 reaction': 'R',
                '1 reaction, which you take when you take acid, cold, fire, lightning, or thunder damage': 'R*',
                '1 reaction, which you take when a humanoid you can see within 60 feet of you dies': 'R*',
                '1 minute': '1m',
                '10 minutes': '10m',
                '1 hour': '1h',
                '8 hours': '8h',
                '1 action or 8 hours': 'A/8h',
                '12 hours': '12h',
                '24 hours': '24h'}
        return abbr[spell.time]

    def abbrev_range(spell):
        """Abbreviate range.

        Possible return values: 10', 120', 500mi, S, S(30'cone), Unlimited, etc
        """
        abbr = {None: "N",
                'Self': 'S',
                'Self (10-foot radius)': "S(10'r)",
                'Self (10-foot-radius sphere)': "S(10'r-sphere)",
                'Self (10-foot-radius hemisphere)': "S(10'r-hemisphere)",
                'Self (15-foot-radius)': "S(15'r)",
                'Self (15-foot cone)': "S(15'cone)",
                'Self (15-foot cube)': "S(15'cube)",
                'Self (30-foot radius)': "S(30'r)",
                'Self (30-foot cone)': "S(30'cone)",
                'Self (60-foot line)': "S(60'line)",
                'Self (60 foot cone)': "S(60'cone)",
                'Self (60-foot cone)': "S(60'cone)",
                'Self (100-foot line)': "S(100'line)",
                'Self (5-mile radius)': "S(5mi.r)",
                'Touch': "T",
                'Special': "Special",
                'Sight': "Sight",
                '5 feet': "5'",
                '10 feet': "10'",
                '15 feet': "15'",
                '30 feet': "30'",
                '60 feet': "60'",
                '90 feet': "90'",
                '100 feet': "100'",
                '120 feet': "120'",
                '150 feet': "150'",
                '300 feet': "300'",
                '500 feet': "500'",
                '1 mile': "1mi",
                '500 miles': "500mi",
                'Unlimited': "Unlimited"}
        return abbr[spell.range]

    def abbrev_duration(spell):
        """Abbreviate spell duration.

        Some possible return values:
        N (none), S (special), 1r (1 round), 1m, 1h, <=1h, C1h (1h concentration)
        """
        abbr = {None: 'N',
                'Instantaneous': 'I',
                'Instantaneous or 1 hour (see below)': 'I/1h',
                'Special': "S",
                '1 turn': '1t',
                'up to 1 round': '<=1r',
                '1 round': '1r',
                'up to 6 rounds': '<=6r',
                'up to 1 minute': "<=1m",
                'Up to 1 minute': '<=1m',
                '1 minute': '1m',
                'up to 10 minutes': "<=10m",
                '10 minutes': '10m',
                'up to 1 hour': "<=1h",
                'Up to 1 hour': '<=1h',
                '1 hour': "1h",
                'up to 2 hours': '<=2h',
                'up to 8 hours': '<=8h',
                'Up to 8 hours': '<=8h',
                '8 hours': "8h",
                'up to 1 day': '<=1d',
                '1 day': '1d',
                '10 days': "10d",
                '24 hours': "24h",
                'up to 24 hours': "<=24h",
                '30 days': '30d',
                '7 days': '7d',
                'Until dispelled or triggered': 'UD/T',
                'Until dispelled': "UD"}

        c = 'C' if spell.concentration else ''
        return c + abbr[spell.duration]

    def abbrev_classes(spell):
        """Abbreviate the classes which have access to a given spell.

        Return values are those from abbrev_class, joined with '+'.
        """
        return '+'.join(Spell.abbrev_class(c) for c in spell.classes)


    def fmt_oneline(spell):
        """Return a string summarizing the spell.

        Format:
            NAME, T/R/D, (L:CLASSES)

        Where
            T = Time
            R = Range
            D = Duration
            L = Level

        >>> test = lambda name: Spells().search(name)[0].fmt_oneline()
        >>> test('Banishing Smite')
        'Banishing Smite B/S/C<=1m (5:P+WlH)'
        >>> test('Identify')
        'Identify (rit.) 1m/T/I (1:A+B+Wz)'
        """
        f = {
            'name': spell.name,
            'rit': ' (rit.)' if spell.ritual else '',
            't': spell.abbrev_time(),
            'r': spell.abbrev_range(),
            'd': spell.abbrev_duration(),
            'l': spell.level,
            'classes': spell.abbrev_classes()}

        return "{name}{rit} {t}/{r}/{d} ({l}:{classes})".format(**f)

    def fmt_pointform(spell, header='-', body='-', tabstop=2):
        """Return multiline string containing all spell information.

        The top line is a one-line header via self.fmt_oneline.
        The remaining lines are the spell text.
        `header` and `body` are single-character bullets
            used for their respective types of lines.
        `tabstop` determines the depth to which the body lines are indented.

        >>> print(Spells().search('Magic Missile')[0].fmt_pointform())
        - Magic Missile A/120'/I (1:FEK+S+Wz)
          - You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
          - 
          - At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.
        >>> print(Spells().search('Magic Missile')[0].fmt_pointform(tabstop=4))
        - Magic Missile A/120'/I (1:FEK+S+Wz)
            - You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
            - 
            - At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.
        >>> print(Spells().search('Magic Missile')[0].fmt_pointform(header='*', body='"'))
        * Magic Missile A/120'/I (1:FEK+S+Wz)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
          " 
          " At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.
        """
        ret = [f'{header} {spell.fmt_oneline()}']
        ret += [f'{" " * tabstop}{body} {line}' for line in spell.text.split('\n')]
        return '\n'.join(ret)


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
    def __init__(self, node):
        """Instantiates this instance using data from the XML `node`."""
        self.__dict__.update(parse.Monster.parse(node))

    def __repr__(self):
        return f"Monster({self.fmt_oneline()})"

    def fmt_oneline(self):
        """Returns a one-line summary of the item.

        >>> Monsters().where(name='Giant Crab')[0].fmt_oneline()
        'Giant Crab: M unaligned beast, 1/8CR 13HP/3d8 15AC (walk 30, swim 30)'
        >>> Monsters().where(name='Crab Folk')[0].fmt_oneline()
        'Crab Folk: L Neutral giant, 3.0CR 68HP/8d10+24 16AC (walk 40, swim 40)'
        """
        fmt = '{name}: {size} {alignment} {type}, {cr}CR {hp}HP/{hitdice} {ac_num}AC ({speeds})'

        fields = ['name', 'size', 'alignment', 'type', 'hp', 'hitdice', 'ac_num']
        # fill `fields` from attributes of `self`
        fields = dict((field, getattr(self, field, '--')) for field in fields)

        cr_table = {0.125: '1/8', 0.25: '1/4', 0.5: '1/2'}
        cr = getattr(self, 'cr', None)
        fields['cr'] = '--' if cr is None else cr_table[cr] if cr % 1 else str(cr)

        speed = getattr(self, 'speed', {'NO': 'MOVEMENT'})
        fields['speeds'] = ', '.join(' '.join([mode, str(dist)]) for mode, dist in speed.items())

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
                        vulnerable=None, description=None):
            text = []
            # * 'name': 1268,
            # * 'alignment': 1252,
            # * 'type': 1268,
            # * 'size': 1268,
            # * 'cr': 1241,
            text.append(f'{name} ({alignment} {type})  Size: {size}  CR: {cr}')

            # * 'hp': 1267,
            #   * 'hitdice': 1261,
            # * 'ac': 1268,
            #   * 'ac_num': 1266,
            # * 'speed': 1267,
            text.append(f'HP: {hp}({hitdice})  AC: {ac}({ac_num})  Speed: {speed}')

            # * 'str': 1268,
            # * 'dex': 1268,
            # * 'con': 1268,
            # * 'int': 1268,
            # * 'wis': 1268,
            # * 'cha': 1268,
            text.append(f'STR:{str} DEX:{dex} CON:{con} INT:{int} WIS:{wis} CHA:{cha}')

            # * 'skills': 877,
            if skills:
                text.append(f'skills: {skills}')
            # * 'saves': 485,
            if saves:
                text.append(f'saves: {saves}')
            # * 'passive': 1264,
            # * 'senses': 881,
            # * 'senses_notes': 3,
            text.append(f'passive perception: {passive}')
            if senses:
                text.append(f'senses: {senses}')
                if senses_notes:
                    text.append(f'NOTE: {senses_notes}')
            # * 'spells': 388,
            if spells:
                text.append(f'spells: {spells}')
            # * 'slots': 203,
            if slots:
                text.append(f'slots: {slots}')

            # * 'armor': 960,
            if armor:
                text.append(f'armor: {armor}')

            # * 'immune': 447,
            # * 'immune_notes': 2,
            # * 'resist': 392,
            # * 'resist_notes': 5,
            # * 'conditionImmune': 449,
            # * 'conditionImmune_notes': 1
            # * 'vulnerable': 51,
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

            return '\n'.join(text)

        fields = ['name', 'alignment', 'type', 'size', 'cr',
                  'hp', 'hitdice', 'ac', 'ac_num', 'speed',
                  'str', 'dex', 'con', 'int', 'wis', 'cha',
                  'skills', 'saves', 'passive', 'senses', 'senses_notes',
                  'spells', 'slots', 'armor', 'immune', 'immune_notes',
                  'resist', 'resist_notes',
                  'conditionImmune', 'conditionImmune_notes',
                  'vulnerable', 'description']

        m = [(f, getattr(self, f, None)) for f in dir(self) if f in fields]
        return render_text(**dict(m))

    def fmt_pointform(self, header='-', body='-', tabstop=2):
        """Multiline string containing point-form summary of item.

        Similar to `Spell.fmt_pointform`.

        First line is simply output of `self.fmt_oneline()`.
        Subsequent lines are any remaining lines after the first two
        in the output of `self.fmt_full()`.

        >>> Monsters().where(name='Goblin').print('pointform')
        - Goblin: S neutral evil humanoid (goblinoid), 1/4CR 7HP/2d6 15AC (walk 30)
          - STR:8 DEX:14 CON:10 INT:10 WIS:8 CHA:8
          - skills: {'Stealth': 6}
          - passive perception: 9
          - senses: {'darkvision': 60}
          - armor: leather armor, shield
        """
        ret = [f'{header} {self.fmt_oneline()}']
        ret += [f'{" " * tabstop}{body} {line}' for line in self.fmt_full().split('\n')[2:]]
        return '\n'.join(ret)

class Collection(list):
    """Virtual superclass for a list of DB items.

    This base class for Monsters and Spells is only useful when subclassed.

    Subclasses implement:
    - _xpath: string, finds all objects of the collection type in the tree
    - type: type the subtype collects
        - e.g. Monsters._type = Monster
    """

    def __init__(self, l=None, tree=None):
        """A list of db objects with added methods.

        With no arguments, returns the list of all db objects of the type, 
        parsing it if needed.

        With a list-like argument, wraps the list and returns it.

        If `tree` is given or if no tree has yet been parsed,
            parses `tree` or the default tree

        If tree was not given, stores the parsed tree in a class
            variable (`_parsed`)
        """
        if l:
            super().__init__(l)
            return

        if hasattr(self, '_parsed') and not tree:
            # if we've already parsed, don't parse again
            super().__init__(self._parsed)
            return

        # otherwise, parse the tree

        store_tree = not tree

        if not tree:
            tree = parse.XML.get_tree()

        objects = tree.xpath(self._xpath)
        super().__init__(self._type(i) for i in objects)
        if store_tree:
            self.__class__._parsed = self

    def search(self, val, field='name'):
        """Case-insensitive contents search over the data set

        Returns items where `field` contains `val`.
        >>> Monsters().search('AAR')[0]
        Monster(Aarakocra: M neutral good humanoid (aarakocra), 1/4CR 13HP/3d8 12AC (walk 20, fly 50))
        >>> Spells().search('smite')[0]
        Spell(Banishing Smite B/S/C<=1m (5:P+WlH))
        """
        def lc_in(term):
            return str(val).lower() in str(getattr(term, field, '')).lower()
        return self.__class__(i for i in self if lc_in(i))

    def filter(self, pred):
        """Returns Collection of the appropriate subclass.

        Collection (e.g. Monsters object) contains items for which pred(item) is True.
        """
        return self.__class__(i for i in self if pred(i))

    def where(self, **kwargs):
        """Filter for items for which all conditions are true.

        If a function-like value is passed, it is treated as a predicate.
        If any other value is passed, it is treated as an == predicate for that value.

        >>> from dnd5edb import predicates as p
        >>> Monsters().where(name='Aarakocra')
        [Monster(Aarakocra: M neutral good humanoid (aarakocra), 1/4CR 13HP/3d8 12AC (walk 20, fly 50))]
        >>> names = lambda mlist: [m.name for m in mlist]
        >>> names(Monsters().where(cr=p.gte(28.0)))
        ['Tarrasque', 'Rak Tulkhesh', 'Sul Khatesh', 'Tiamat']
        >>> names(Monsters().where(cr=p.gt(28.0)))
        ['Tarrasque', 'Tiamat']
        >>> names(Monsters().where(cr=3.0, senses=p.key('blindsight')))[0:4]
        ['Blue Dragon Wyrmling', 'Giant Scorpion', 'Gold Dragon Wyrmling', 'Grell']
        >>> Monsters().where(cr=3.0, int=p.gt(16)).where(int=p.lte(17))
        [Monster(Merrenoloth: M neutral evil fiend (yugoloth), 3.0CR 40HP/9d8 13AC (walk 30, swim 40))]
        >>> Monsters().where(speed=p.key('swim'))[0]
        Monster(Aboleth: L lawful evil aberration, 10.0CR 135HP/18d10+36 17AC (walk 10, swim 40))
        >>> Monsters().where(spells=p.in_('conjure animals'))[0].name
        'Drow Priestess of Lolth'
        """
        result = self
        for field, value in kwargs.items():
            if hasattr(value, '__call__'):
                pred = value
            else:
                pred = predicates.eq(value)

            result = result.filter(partial(pred, field))

        return result

    where_fields = reflect.collection_attribs

    def sorted(self, field='name'):
        """Copies self, sorts the internal data using key `name`; returns copy.

        >>> s = Spells()
        >>> from dnd5edb import predicates as p
        >>> s = s.where(text=p.in_('adiant')).where(classes=p.in_('Warlock'))
        >>> s = s.sorted('name')
        >>> s.sorted('level').print()
        Shadow of Moil A/S/C<=1m (4:Wl)
        Sickening Radiance A/120'/C<=10m (4:FEK+S+Wl+Wz)
        Wall of Light A/120'/C<=10m (5:S+Wl+Wz)
        Crown of Stars A/S/1h (7:S+Wl+Wz)
        >>> s.sorted('classes').print()
        Sickening Radiance A/120'/C<=10m (4:FEK+S+Wl+Wz)
        Crown of Stars A/S/1h (7:S+Wl+Wz)
        Wall of Light A/120'/C<=10m (5:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m (4:Wl)
        >>> s.sorted('sources').print() # still sorted by name
        Crown of Stars A/S/1h (7:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m (4:Wl)
        Sickening Radiance A/120'/C<=10m (4:FEK+S+Wl+Wz)
        Wall of Light A/120'/C<=10m (5:S+Wl+Wz)
        >>> s.sorted('blipdebloop').print()
        Traceback (most recent call last):
          ...
        TypeError: '<' not supported between instances of 'NoneType' and 'NoneType'
        """
        copy = Spells(self.copy())
        copy.sort(key=lambda o: getattr(o, field, None))
        return copy

    def extend(self, new_items):
        """Adds to `self` any items from `new_items` not already in `self`.

        >>> from dnd5edb import predicates as p
        >>> s = Spells()
        >>> # Celestial Warlock spells containing "adiant" or case-insensitive "fire"
        >>> (s.where(text=p.in_('adiant')).extend(s.where(text=p.in_('fire')))
        ...   .extend(s.where(text=p.in_('Fire'))).where(classes=p.or_(p.in_('Warlock'),
        ...                                                            p.in_('Warlock (Celestial)')))
        ...   .sorted('name').sorted('level').print())
        Create Bonfire A/60'/C<=1m (0:A+D+FEK+AT+S+Wl+Wz)
        Greenflame Blade A/5'/I (0:FEK+AT+S+Wl+Wz)
        Prestidigitation A/10'/<=1h (0:A+B+FEK+AT+S+Wl+Wz)
        Guiding Bolt A/120'/1r (1:C+WlC)
        Hellish Rebuke R/60'/I (1:Wl)
        Unseen Servant (rit.) A/60'/1h (1:B+Wl+Wz)
        Flaming Sphere A/60'/C<=1m (2:D+WlC+Wz)
        Elemental Bane A/90'/C<=1m (4:A+D+Wl+Wz)
        Guardian of Faith A/30'/8h (4:C+WlC)
        Shadow of Moil A/S/C<=1m (4:Wl)
        Sickening Radiance A/120'/C<=10m (4:FEK+S+Wl+Wz)
        Wall of Fire A/120'/C<=1m (4:D+FEK+S+WlC+WlF+Wz)
        Flame Strike A/60'/I (5:C+WlC+WlF)
        Wall of Light A/120'/C<=10m (5:S+Wl+Wz)
        Investiture of Flame A/S/C<=10m (6:D+S+Wl+Wz)
        Investiture of Ice A/S/C<=10m (6:D+S+Wl+Wz)
        Mental Prison A/60'/C<=1m (6:S+Wl+Wz)
        Crown of Stars A/S/1h (7:S+Wl+Wz)
        Plane Shift A/T/I (7:C+D+S+Wl+Wz)
        """
        for i in new_items:
            if i not in self:
                self.append(i)
        return self

    # TODO: move this into Collection and add Monsters doctests
    def fmt(self, method='oneline', **kwargs):
        """Returns newline-separated results of calling `method` for each item.

        By default, uses the one-line format method for the given item type.

        >>> from dnd5edb import predicates as p
        >>> print(Spells().where(name=p.in_('Circle')).fmt())
        Circle of Death A/150'/I (6:S+Wl+Wz)
        Circle of Power A/S(30'r)/C<=10m (5:P)
        Circle of Power* A/S(30'r)/C<=10m (5:PCr)
        Magic Circle 1m/10'/1h (3:C+FEK+P+RMS+Wl+Wz)
        Magic Circle* 1m/10'/1h (3:CA)
        Teleportation Circle 1m/10'/1r (5:B+RHW+S+Wz)
        Teleportation Circle* 1m/10'/1r (5:CA)
        >>> print(Spells().where(name=p.in_('Find')).where(name=p.in_('Steed')).fmt('xlist'))
        * Find Steed 10m/30'/I (2:P)
          " You summon a spirit that assumes the form of an unusually intelligent, strong, and loyal steed, creating a long-lasting bond with it. Appearing in an unoccupied space within range, the steed takes on a form that you choose: a warhorse, a pony, a camel, an elk, or a mastiff. (Your DM might allow other animals to be summoned as steeds.) The steed has the statistics of the chosen form, though it is a celestial, fey, or fiend (your choice) instead of its normal type. Additionally, if your steed has an Intelligence of 5 or less, its Intelligence becomes 6, and it gains the ability to understand one language of your choice that you speak.
          " Your steed serves you as a mount, both in combat and out, and you have an instinctive bond with it that allows you to fight as a seamless unit. While mounted on your steed, you can make any spell you cast that targets only you also target your steed.
          " When the steed drops to 0 hit points, it disappears, leaving behind no physical form. You can also dismiss your steed at any time as an action, causing it to disappear. In either case, casting this spell again summons the same steed, restored to its hit point maximum.
          " While your steed is within 1 mile of you, you can communicate with it telepathically.
          " You can't have more than one steed bonded by this spell at a time. As an action, you can release the steed from its bond at any time, causing it to disappear.
        * Find Greater Steed 10m/30'/I (4:P)
          " You summon a spirit that assumes the form of a loyal, majestic mount. Appearing in an unoccupied space within range, the spirit takes on a form you choose: a griffon, a pegasus, a peryton, a dire wolf, a rhinoceros, or a saber-toothed tiger. The creature has the statistics provided in the Monster Manual for the chosen form, though it is a celestial, a fey, or a fiend (your choice) instead of its normal creature type. Additionally, if it has an Intelligence score of 5 or lower, its Intelligence becomes 6, and it gains the ability to understand one language of your choice that you speak.
          " 
          " You control the mount in combat. While the mount is within 1 mile of you, you can communicate with it telepathically. While mounted on it, you can make any spell you cast that targets only you also target the mount.
          " 
          " The mount disappears temporarily when it drops to 0 hit points or when you dismiss it as an action. Casting this spell again re-summons the bonded mount, with all its hit points restored and any conditions removed.
          " 
          " You can’t have more than one mount bonded by this spell or find steed at the same time. As an action, you can release a mount from its bond, causing it to disappear permanently.
          " 
          " Whenever the mount disappears, it leaves behind any objects it was wearing or carrying.
        """
        return '\n'.join(getattr(i, 'fmt_' + method)(**kwargs) for i in self)

    def print(self, *args, **kwargs):
        """CLI convenience function.

        Passes args to self.fmt, prints result.
        """
        print(self.fmt(*args, **kwargs))

class Spells(Collection):
    """A list of spells from the db.

    If passed a list of spells, wraps it with formatting methods.
    If not, uses the full set of spells from the DB instead.
    """

    _xpath = '//spell'
    _type = Spell

    def search_desc(self, val):
        return self.search(val, field='text')

    # kind of an example function.
    def oneline_desc(self, string):
        """Returns one-line summaries of all spells with `string` in their descriptions."""
        return '\n'.join(Spell.fmt_oneline(s) for s in self.search_desc(string))

    def csv_table(self):
        """Returns CSV tabular data with a header for the contents of this list."""
        fields = ['name', 't', 'r', 'd', 'l']
        fields += [Spell.abbrev_class(c) for c in Spell.char_classes]
        lines = [', '.join(fields)]

        lines += [Spell.summary_class_columns(s, Spell.char_classes)
                  for s in self]

        return "\n".join(lines)

class Monsters(Collection):
    """List of all the <monster> entries in the db.

    >>> monster = lambda name: next(m for m in Monsters() if m.name == name)
    >>> monster('Champion').ac_num
    18
    >>> monster('Champion').armor
    'plate'
    >>> monster('Cow').armor
    Traceback (most recent call last):
        ...
    AttributeError: 'Monster' object has no attribute 'armor'
    >>> monster('Froghemoth').hp
    184
    >>> monster('Froghemoth').hitdice
    '16d12+80'
    >>> monster('Astral Dreadnought').speed
    {'walk': 15, 'fly': 80}
    >>> monster('Aarakocra')
    Monster(Aarakocra: M neutral good humanoid (aarakocra), 1/4CR 13HP/3d8 12AC (walk 20, fly 50))
    >>> monster('Duergar Warlord')
    Monster(Duergar Warlord: M lawful evil humanoid (dwarf), 6.0CR 75HP/10d8+30 20AC (walk 25))
    >>> monster('War Priest')
    Monster(War Priest: M any alignment humanoid (any race), 9.0CR 117HP/18d8+36 18AC (walk 30))
    >>> Monsters(m for m in Monsters() if getattr(m, 'name').startswith('C'))[0]
    Monster(Cambion: M any evil alignment fiend, 5.0CR 82HP/11d8+33 19AC (walk 30, fly 60))
    """
    _xpath = '//monster'
    _type = Monster
