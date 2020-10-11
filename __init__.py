from functools import partial
from dnd5edb import parse, predicates

class Spell:
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

    def fmt_pointform(spell, header='-', text='-', tabstop=2):
        """Return multiline string containing all spell information.

        The top line is a one-line header via self.fmt_oneline.
        The remaining lines are the spell text.
        `header` and `text` are single-character bullets
            used for their respective types of lines.
        `tabstop` determines the depth to which the text lines are indented.

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
        >>> print(Spells().search('Magic Missile')[0].fmt_pointform(header='*', text='"'))
        * Magic Missile A/120'/I (1:FEK+S+Wz)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
          " 
          " At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.
        """
        ret = [f'{header} {spell.fmt_oneline()}']
        ret += [f'{" " * tabstop}{text} {line}' for line in spell.text.split('\n')]
        return '\n'.join(ret)

    def fmt_xlist(spell, tabstop=2):
        """Pointform output in xlist format.

        >>> print(Spells().search('Magic Missile')[0].fmt_xlist())
        * Magic Missile A/120'/I (1:FEK+S+Wz)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
          " 
          " At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.
        """
        return spell.fmt_pointform(header='*', text='"', tabstop=tabstop)


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

class Monster:
    def __init__(self, node):
        """Instantiates this instance using data from the XML `node`."""
        self.__dict__.update(parse.Monster.parse(node))

    def __repr__(self):
        return f"Monster({{'name': {self.name}, 'type': {self.type}}})"

    def fulltext(self):
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
        Monster({'name': Aarakocra, 'type': humanoid (aarakocra)})
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
        [Monster({'name': Aarakocra, 'type': humanoid (aarakocra)})]
        >>> names = lambda mlist: [m.name for m in mlist]
        >>> names(Monsters().where(cr=p.gt(28.0)))
        ['Tarrasque', 'Rak Tulkhesh', 'Sul Khatesh', 'Tiamat']
        >>> names(Monsters().where(cr=3.0, senses=p.key('blindsight')))[0:4]
        ['Blue Dragon Wyrmling', 'Giant Scorpion', 'Gold Dragon Wyrmling', 'Grell']
        >>> Monsters().where(cr=3.0, int=p.gte(16)).where(int=p.lte(17))
        [Monster({'name': Merrenoloth, 'type': fiend (yugoloth)})]
        >>> Monsters().where(speed=p.key('swim'))[0]
        Monster({'name': Aboleth, 'type': aberration})
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
    Monster({'name': Aarakocra, 'type': humanoid (aarakocra)})
    >>> monster('Duergar Warlord')
    Monster({'name': Duergar Warlord, 'type': humanoid (dwarf)})
    >>> monster('War Priest')
    Monster({'name': War Priest, 'type': humanoid (any race)})
    >>> Monsters(m for m in Monsters() if getattr(m, 'name').startswith('C'))[0]
    Monster({'name': Cambion, 'type': fiend})
    """
    _xpath = '//monster'
    _type = Monster
