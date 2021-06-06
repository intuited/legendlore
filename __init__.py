from functools import partial
from dnd5edb import parse, predicates, reflect, datatypes

class DBItem:
    """Abstract base class for Spell, Monster, and other database entries."""
    def fmt_xlist(self, tabstop=2):
        """Pointform output in xlist format.

        DBItem subclass must implement fmt_pointform for this to work.

        >>> print(Spells().search('Magic Missile')[0].fmt_xlist())
        * Magic Missile A/120'/I [V/S] (1:AArm+CA+S+Wz)
          " Evocation (PHB#257)
          " You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4 + 1 force damage to its target. The darts all strike simultaneously, and you can direct them to hit one creature or several.
          " At Higher Levels:
          " When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot level above 1st.
        >>> print(Monsters().search('Griffon')[0].fmt_xlist()) # doctest: +ELLIPSIS
        * Griffon: L Unaligned monstrosity, 2.0CR 59HP/7d10+21 12AC (walk 30, fly 80)
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
        * Wall of Water A/60'/C<=10m [V/S] (3:D+S+Wz)
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
    def __init__(self, node):
        """Instantiates this instance using data from the XML `node`."""
        self.__dict__.update(parse.MonsterParser.parse(node))

    def __repr__(self):
        return f"Monster({self.fmt_oneline()})"

    def fmt_oneline(self):
        """Returns a one-line summary of the item.

        >>> Monsters().where(name='Giant Crab')[0].fmt_oneline()
        'Giant Crab: M Unaligned beast, 1/8CR 13HP/3d8 15AC (walk 30, swim 30)'
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
                        vulnerable=None, description=None, action=None):
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

            if action:
                text.append('ACTIONS:')
                for name, details in action.items():
                    text.append(f'{name}: {details.get("text", "")}')

            return '\n'.join(text)

        fields = ['name', 'alignment', 'type', 'size', 'cr',
                  'hp', 'hitdice', 'ac', 'ac_num', 'speed',
                  'str', 'dex', 'con', 'int', 'wis', 'cha',
                  'skills', 'saves', 'passive', 'senses', 'senses_notes',
                  'spells', 'slots', 'armor', 'immune', 'immune_notes',
                  'resist', 'resist_notes',
                  'conditionImmune', 'conditionImmune_notes',
                  'vulnerable', 'description', 'action']

        fields = dict((f, getattr(self, f, None)) for f in dir(self) if f in fields)
        return render_text(**fields)

    def fmt_pointform(self, header='-', body='-', tabstop=2):
        """Multiline string containing point-form summary of item.

        Similar to `Spell.fmt_pointform`.

        First line is simply output of `self.fmt_oneline()`.
        Subsequent lines are any remaining lines after the first two
        in the output of `self.fmt_full()`.

        >>> Monsters().where(name='Goblin').print('pointform') # doctest: +ELLIPSIS
        - Goblin: S Neutral Evil humanoid (goblinoid), 1/4CR 7HP/2d6 15AC (walk 30)
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
        if l is not None:
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
        self._apply_errata()
        if store_tree:
            self.__class__._parsed = self

    def __getitem__(self, key):
        """Return a collection of the same type if `key` is a slice.

        >>> from repltools import s
        >>> s.where(level=1)[:4].print()
        Absorb Elements R/S/1r [S] (1:A+D+Ra+S+Wz)
        Alarm (rit.) 1m/30'/8h [V/S] (1:A+PW+Ra+SCS+Wz)
        Animal Friendship A/30'/24h [V/S] (1:Bd+CN+D+Ra)
        Armor of Agathys A/S/1h [V/S] (1:PCo+Wl)
        >>> type(s.where(level=1)[:4])
        <class 'dnd5edb.Spells'>
        """
        ret = super().__getitem__(key)
        if type(key) is slice:
            return type(self)(ret)
        else:
            return ret

    def _apply_errata(self):
        """Subclass hook to make changes to the DB after parsing."""
        return

    def search(self, val, field='name'):
        """Case-insensitive contents search over the data set

        Returns items where `field` contains `val`.
        >>> Monsters().search('AAR')[0]
        Monster(Aarakocra: M Neutral Good humanoid (aarakocra), 1/4CR 13HP/3d8 12AC (walk 20, fly 50))
        >>> Spells().search('smite')[0]
        Spell(Banishing Smite B/S/C<=1m [V] (5:ABS+P+WlH))
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
        [Monster(Aarakocra: M Neutral Good humanoid (aarakocra), 1/4CR 13HP/3d8 12AC (walk 20, fly 50))]
        >>> names = lambda mlist: [m.name for m in mlist]
        >>> names(Monsters().where(cr=p.gte(28.0)))
        ['Rak Tulkhesh', 'Sul Khatesh', 'Tarrasque', 'Tiamat']
        >>> names(Monsters().where(cr=p.gt(28.0)))
        ['Tarrasque', 'Tiamat']
        >>> names(Monsters().where(cr=3.0, senses=p.key('blindsight')))[0:4]
        ['Animated Stove', 'Assassin Vine', 'Blue Dragon Wyrmling', 'Brain in a Jar']
        >>> Monsters().where(cr=3.0, int=p.gt(16)).where(int=p.lte(17))
        [Monster(Merrenoloth: M Neutral Evil fiend (yugoloth), 3.0CR 40HP/9d8 13AC (walk 30, swim 40))]
        >>> Monsters().where(speed=p.key('swim'))[0]
        Monster(Beast of the Sea: M Unaligned beast, --CR 5HP/-- 0AC (walk 5, swim 60))
        >>> Monsters().where(spells=p.contains('conjure animals'))[0].name
        'Horncaller'
        """
        result = self
        for field, value in kwargs.items():
            if hasattr(value, '__call__'):
                pred = value
            else:
                pred = predicates.eq(value)

            result = result.filter(partial(pred, field))

        return self._post_process_where(result)

    where_fields = reflect.collection_attribs

    def _post_process_where(self, result):
        """Hook to, for example, change sort order for results returned by Collection.where

        Default implementation simply returns `result`.
        """
        return result

    def sorted(self, field='name', key=None, reverse=False):
        """Copies self, sorts the internal data using field `name` by default; returns copy.

        If `key` is specified, uses that key function instead of the default getter.
        Key functions take a single parameter, the object whose key is being retrieved.

        >>> from repltools import m, s, p
        >>> s = s.where(text=p.contains('adiant')).where(classes=p.contains('Warlock'))
        >>> s = s.sorted('name')
        >>> s.sorted('level').print()
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S] (5:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        >>> s.sorted('level', reverse=True).print()
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S] (5:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        >>> s.sorted('classes').print()
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S] (5:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)

        # Sorting by level does not disturb previous sort by name
        >>> s.sorted('sources').print()
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S] (5:S+Wl+Wz)

        Invalid sort fields have no effect
        >>> s.sorted('blipdebloop').print()
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S] (5:S+Wl+Wz)

        Test that we're handling empty sets correctly
        >>> len(s.where(classes=p.contains('gobbledegook')).sorted())
        0

        Same stuff works for monsters
        >>> m.where(type='beast', cr=4).sorted('hp').print()
        Giant Subterranean Lizard: H Unaligned beast, 4.0CR 66HP/7d12+21 14AC (walk 30, swim 50)
        Elephant: H Unaligned beast, 4.0CR 76HP/8d12+24 12AC (walk 40)
        Stegosaurus: H Unaligned beast, 4.0CR 76HP/8d12+24 13AC (walk 40)
        Giant Walrus: H Unaligned beast, 4.0CR 85HP/9d12+27 9AC (walk 20, swim 40)
        Giant Coral Snake: L Unaligned beast, 4.0CR 90HP/12d10+24 13AC (walk 30, swim 30)
        >>> m.where(speed=p.contains('swim'), type=p.eq('beast')).sorted('cr')[:6].print()
        Beast of the Sea: M Unaligned beast, --CR 5HP/-- 0AC (walk 5, swim 60)
        Bestial Spirit: S Unaligned beast, --CR 20HP/-- 0AC (walk 30, climb 30, fly 60, swim 30)
        Crab: T Unaligned beast, 0.0CR 2HP/1d4 11AC (walk 20, swim 20)
        Fish: T Unaligned beast, 0.0CR 1HP/1d4-1 13AC (swim 40)
        Frog: T Unaligned beast, 0.0CR 1HP/1d4-1 11AC (walk 20, swim 20)
        Kingsport: M Unaligned beast, 0.0CR 5HP/1d8+1 11AC (walk 20, swim 40)
        >>> m.where(speed=p.contains('swim'), type=p.eq('beast')).sorted('cr', reverse=True)[:2].print()
        Huge Giant Crab: H Unaligned beast, 8.0CR 161HP/14d12+70 15AC (walk 30, swim 30)
        Sperm Whale: G Unaligned beast, 8.0CR 189HP/14d20+42 13AC (walk 0, swim 60)
        >>> animat = m.where(type='construct', name=p.contains('Animat')).sorted('cr')
        >>> [getattr(n, 'cr', '--') for n in animat]
        ['--', '--', '--', '--', '--', '--', '--', 0.25, 0.25, 0.25, 1.0, 1.0, 2.0, 2.0, 3.0, 6.0, 10.0]
        >>> animat = m.where(type='construct', name=p.contains('Animat')).sorted('cr', reverse=True)
        >>> [getattr(n, 'cr', '--') for n in animat]
        [10.0, 6.0, 3.0, 2.0, 2.0, 1.0, 1.0, 0.25, 0.25, 0.25, '--', '--', '--', '--', '--', '--', '--']
        """
        if key == None:
            key = lambda o: getattr(o, field, None)

        # pull out nodes that lack the field
        without_field = [n for n in self if key(n) is None]
        with_field = [n for n in self if key(n) is not None]

        # sort the nodes that have the field
        with_field.sort(key=key, reverse=reverse)

        # return None values at the low end of the list
        if not reverse:
            ret = without_field + with_field
        else:
            ret = with_field + without_field

        return type(self)(ret)

    def extend(self, new_items):
        """Adds to `self` any items from `new_items` not already in `self`.

        >>> from dnd5edb import predicates as p
        >>> s = Spells()
        >>> # Celestial Warlock spells containing "adiant" or case-insensitive "fire"
        >>> (s.where(text=p.contains('adiant')).extend(s.where(text=p.contains('fire')))
        ...   .extend(s.where(text=p.contains('Fire'))).where(classes=p.or_(p.contains('Warlock'),
        ...                                                                 p.contains('Warlock (Celestial)')))
        ...   .sorted('name').sorted('level').print())
        Create Bonfire A/60'/C<=1m [V/S] (0:A+D+S+Wl+Wz)
        Green-Flame Blade A/S(5'r)/I [V/M@0.1gp] (0:A+S+Wl+Wz)
        Prestidigitation A/10'/1h [V/S] (0:A+Bd+FAA+S+Wl+Wz)
        Sacred Flame A/60'/I [V/S] (0:C+WlC)
        Guiding Bolt A/120'/1r [V/S] (1:C+PG+WlC)
        Hellish Rebuke R/60'/I [V/S] (1:PO+Wl)
        Unseen Servant (rit.) A/60'/1h [V/S] (1:Bd+Wl+Wz)
        Flaming Sphere A/60'/C<=1m [V/S] (2:AAl+CLt+D+DW+S+WlC+Wz)
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Elemental Bane A/90'/C<=1m [V/S] (4:A+D+Wl+Wz)
        Guardian of Faith A/30'/8h [V] (4:C+CLf+CLt+PCr+PD+WlC)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Wall of Fire A/120'/C<=1m [V/S] (4:AArt+CF+CLt+D+S+WlC+WlFi+Wz)
        Flame Strike A/60'/I [V/S] (5:C+CLt+CW+DW+PD+PG+WlC+WlFi+WlGe)
        Wall of Light A/120'/C<=10m [V/S] (5:S+Wl+Wz)
        Investiture of Flame A/S/C<=10m [V/S] (6:D+S+Wl+Wz)
        Investiture of Ice A/S/C<=10m [V/S] (6:D+S+Wl+Wz)
        Mental Prison A/60'/C<=1m [S] (6:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Plane Shift A/T/I [V/S/M@250gp] (7:C+D+S+Wl+Wz)
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
        >>> print(Spells().where(name=p.contains('Circle')).fmt())
        Magic Circle 1m/10'/1h [V/S/M@!100!gp] (3:C+CA+P+RaMS+Wl+Wz)
        Circle of Power A/S(30'r)/C<=10m [V] (5:CTw+P+PCr)
        Teleportation Circle 1m/10'/1r [V/M@!50!gp] (5:Bd+CA+RaHW+S+Wz)
        Circle of Death A/150'/I [V/S/M@500gp] (6:S+Wl+Wz)
        >>> print(Spells().where(name=p.contains('Find')).where(name=p.contains('Steed')).fmt('xlist'))
        * Find Steed 10m/30'/I [V/S] (2:P)
          " Conjuration (PHB#240)
          " You summon a spirit that assumes the form of an unusually intelligent, strong, and loyal steed, creating a long-lasting bond with it. Appearing in an unoccupied space within range, the steed takes on a form that you choose: a warhorse, a pony, a camel, an elk, or a mastiff. (Your DM might allow other animals to be summoned as steeds.) The steed has the statistics of the chosen form, though it is a celestial, fey, or fiend (your choice) instead of its normal type. Additionally, if your steed has an Intelligence of 5 or less, its Intelligence becomes 6, and it gains the ability to understand one language of your choice that you speak.
          " Your steed serves you as a mount, both in combat and out, and you have an instinctive bond with it that allows you to fight as a seamless unit. While mounted on your steed, you can make any spell you cast that targets only you also target your steed.
          " When the steed drops to 0 hit points, it disappears, leaving behind no physical form. You can also dismiss your steed at any time as an action, causing it to disappear. In either case, casting this spell again summons the same steed, restored to its hit point maximum.
          " While your steed is within 1 mile of you, you can communicate with each other telepathically.
          " You can't have more than one steed bonded by this spell at a time. As an action, you can release the steed from its bond at any time, causing it to disappear.
        * Find Greater Steed 10m/30'/I [V/S] (4:P)
          " Conjuration (XGtE#156)
          " You summon a spirit that assumes the form of a loyal, majestic mount. Appearing in an unoccupied space within range, the spirit takes on a form you choose: a griffon, a pegasus, a peryton, a dire wolf, a rhinoceros, or a saber-toothed tiger. The creature has the statistics provided in the Monster Manual for the chosen form, though it is a celestial, a fey, or a fiend (your choice) instead of its normal creature type. Additionally, if it has an Intelligence score of 5 or lower, its Intelligence becomes 6, and it gains the ability to understand one language of your choice that you speak.
          " You control the mount in combat. While the mount is within 1 mile of you, you can communicate with it telepathically. While mounted on it, you can make any spell you cast that targets only you also target the mount.
          " The mount disappears temporarily when it drops to 0 hit points or when you dismiss it as an action. Casting this spell again re-summons the bonded mount, with all its hit points restored and any conditions removed.
          " You can't have more than one mount bonded by this spell or find steed at the same time. As an action, you can release a mount from its bond, causing it to disappear permanently.
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

    def _apply_errata(self):
        """Fix errors from the XML file that can be handled at the object level.

        ### Errata 1: some classes appear twice in <spell> classes lists.

        With this method in place, this should be fixed.
        >>> Spells().where(name="Acid Splash")[0].classes
        ['Artificer', 'Sorcerer', 'Wizard']

        ### Errata 2: Some spells are in the DB twice.

        The entries appear to be identical except that the `sources` attribute of one is a superset of the other's.

        These five spells each have two copies in the CoreOnly XML file.
        >>> dupspells = ['Booming Blade', 'Green-Flame Blade', 'Lightning Lure', 'Sword Burst', 'Blade of Disaster']

        With this method in place, there should be 1 of each in the Spells DB.
        >>> [len(Spells().where(name=spellname)) for spellname in dupspells]
        [1, 1, 1, 1, 1]

        And there should be 2 sources for each of these spells.
        >>> [len(Spells().where(name=spellname)[0].sources) for spellname in dupspells]
        [2, 2, 2, 2, 2]
        """
        # Some classes appear twice; eliminate this issue
        for spell in self:
            spell.classes = sorted(list(set(spell.classes)))

        # find the duplicates
        dupspells = []
        for i in range(0, len(self)):
            if self[i].name in [j.name for j in self[i+1:]]:
                dupspells += [self[i].name]

        for spellname in dupspells:
            dupes = self.where(name=spellname)
            # sort by # of sources, leave the highest
            dupes_to_delete = sorted(dupes, key=lambda spell: len(spell.sources))[:-1]
            for dupe in dupes_to_delete:
                self.remove(dupe)

    def search_desc(self, val):
        return self.search(val, field='text')

    def _post_process_where(self, result):
        """Sort by name and level."""
        return result.sorted('name').sorted('level')

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
    'plate armor'
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
    Monster(Aarakocra: M Neutral Good humanoid (aarakocra), 1/4CR 13HP/3d8 12AC (walk 20, fly 50))
    >>> monster('Duergar Warlord')
    Monster(Duergar Warlord: M Lawful Evil humanoid (dwarf), 6.0CR 75HP/10d8+30 20AC (walk 25))
    >>> monster('War Priest')
    Monster(War Priest: M Any alignment humanoid (any race), 9.0CR 117HP/18d8+36 18AC (walk 30))
    >>> Monsters(m for m in Monsters() if getattr(m, 'name').startswith('C'))[0]
    Monster(Cambion: M Any Evil Alignment fiend, 5.0CR 82HP/11d8+33 19AC (walk 30, fly 60))
    """
    _xpath = '//monster'
    _type = Monster

    def _post_process_where(self, result):
        """Sort by name and level."""
        return result.sorted('name').sorted('cr')
