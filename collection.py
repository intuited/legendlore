from functools import partial
from legendlore import parse, predicates, reflect, db_items
from legendlore.util import careful_sum
import pprint as pp_module

pprint = partial(pp_module.pprint, sort_dicts=False)

class Collection(list):
    """Virtual superclass for a list of DB items.

    This base class for Monsters and Spells is only useful when subclassed.

    Subclasses implement:
    - _xpath: string, finds all objects of the collection type in the tree
    - type: type the subtype collects
        - e.g. Monsters._type = Monster
    """

    def __init__(self, l=None, tree=None, name=None):
        """A list of db objects with added methods.

        With no arguments, returns the list of all db objects of the type, 
        parsing it if needed.

        With a list-like argument, wraps the list and returns it.

        If `tree` is given or if no tree has yet been parsed,
            parses `tree` or the default tree

        If tree was not given, stores the parsed tree in a class
            variable (`_parsed`)

        `name` can be used to assign an arbitrary name to the collection,
        for example 'party' when simulating the party's combat abilities.
        """
        if l is not None:
            super().__init__(l)
            if name:
                self.name = name
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
        Alarm (rit.) 1m/30'/8h [V/S/M] (1:A+PW+Ra+SCS+Wz)
        Animal Friendship A/30'/24h [V/S/M] (1:Bd+CN+D+Ra)
        Armor of Agathys A/S/1h [V/S/M] (1:PCo+Wl)
        >>> type(s.where(level=1)[:4])
        <class 'legendlore.collection.Spells'>
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
        Monster(Aarakocra: M NG humanoid (aarakocra), 1/4CR DPR=4.1/2.8/1.4 13HP/3d8 12AC (walk 20, fly 50))
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

    def text_match(self, text):
        """Case-insensitive search over all text fields.

        >>> from legendlore.repltools import *
        >>> pp(m.text_match('aaqa'))
        [Monster(Aarakocra: M NG humanoid (aarakocra), 1/4CR DPR=4.1/2.8/1.4 13HP/3d8 12AC (walk 20, fly 50)),
         Monster(Gargoyle: M CE elemental, 2.0CR DPR=8.2/5.5/2.8 52HP/7d8+21 15AC (walk 30, fly 60)),
         Monster(Asharra: M LN humanoid (aarakocra), 2.0CR DPR=4.1/2.8/1.4 31HP/7d8 12AC (walk 20, fly 50)),
         Monster(Mwaxanaré: M LN humanoid (human), 1/8CR DPR=1.6/1.0/0.4 13HP/3d8 10AC (walk 30))]
        """
        return self.__class__(i for i in self if i.text_match(text))

    def where(self, **kwargs):
        """Filter for items for which all conditions are true.

        If a function-like value is passed, it is treated as a predicate.
        If any other value is passed, it is treated as an == predicate for that value.

        >>> from legendlore import predicates as p
        >>> Monsters().where(name='Aarakocra')
        [Monster(Aarakocra: M NG humanoid (aarakocra), 1/4CR DPR=4.1/2.8/1.4 13HP/3d8 12AC (walk 20, fly 50))]
        >>> names = lambda mlist: [m.name for m in mlist]
        >>> names(Monsters().where(cr=p.gte(28.0)))
        ['Rak Tulkhesh', 'Sul Khatesh', 'Tarrasque', 'Tiamat']
        >>> names(Monsters().where(cr=p.gt(28.0)))
        ['Tarrasque', 'Tiamat']
        >>> names(Monsters().where(cr=3.0, senses=p.key('blindsight')))[0:4]
        ['Animated Stove', 'Assassin Vine', 'Blue Dragon Wyrmling', 'Brain in a Jar']
        >>> Monsters().where(cr=3.0, int=p.gt(16)).where(int=p.lte(17))
        [Monster(Merrenoloth: M NE fiend (yugoloth), 3.0CR DPR>=~6.4/4.4/2.4 40HP/9d8 13AC (walk 30, swim 40))]
        >>> Monsters().where(speed=p.key('swim'))[0]
        Monster(Beast of the Sea: M UA beast, --CR DPR:?? 5HP/-- 0AC (walk 5, swim 60))
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
        Wall of Light A/120'/C<=10m [V/S/M] (5:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        >>> s.sorted('level', reverse=True).print()
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S/M] (5:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        >>> s.sorted('classes').print()
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S/M] (5:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)

        # Sorting by level does not disturb previous sort by name
        >>> s.sorted('sources').print()
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S/M] (5:S+Wl+Wz)

        Invalid sort fields have no effect
        >>> s.sorted('blipdebloop').print()
        Crown of Stars A/S/1h [V/S] (7:S+Wl+Wz)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Tasha's Otherworldly Guise B/S/C<=1m [V/S/M@500gp] (6:S+Wl+Wz)
        Wall of Light A/120'/C<=10m [V/S/M] (5:S+Wl+Wz)

        Test that we're handling empty sets correctly
        >>> len(s.where(classes=p.contains('gobbledegook')).sorted())
        0

        Same stuff works for monsters
        >>> m.where(type='beast', cr=4).sorted('hp').print()
        Giant Subterranean Lizard: H UA beast, 4.0CR DPR>=~14.4/10.4/6.4 66HP/7d12+21 14AC (walk 30, swim 50)
        Elephant: H UA beast, 4.0CR DPR=21.4/15.8/10.1 76HP/8d12+24 12AC (walk 40)
        Stegosaurus: H UA beast, 4.0CR DPR=23.4/16.9/10.4 76HP/8d12+24 13AC (walk 40)
        Giant Walrus: H UA beast, 4.0CR DPR=29.9/22.1/14.2 85HP/9d12+27 9AC (walk 20, swim 40)
        Giant Coral Snake: L UA beast, 4.0CR DPR=6.4/4.4/2.4 90HP/12d10+24 13AC (walk 30, swim 30)
        >>> m.where(speed=p.contains('swim'), type=p.eq('beast')).sorted('cr')[:6].print()
        Beast of the Sea: M UA beast, --CR DPR:?? 5HP/-- 0AC (walk 5, swim 60)
        Bestial Spirit: S UA beast, --CR DPR:?? 20HP/-- 0AC (walk 30, climb 30, fly 60, swim 30)
        Crab: T UA beast, 0.0CR DPR:?? 2HP/1d4 11AC (walk 20, swim 20)
        Fish: T UA beast, 0.0CR DPR:?? 1HP/1d4-1 13AC (swim 40)
        Frog: T UA beast, 0.0CR DPR:?? 1HP/1d4-1 11AC (walk 20, swim 20)
        Kingsport: M UA beast, 0.0CR DPR=2.5/1.6/0.7 5HP/1d8+1 11AC (walk 20, swim 40)
        >>> m.where(speed=p.contains('swim'), type=p.eq('beast')).sorted('cr', reverse=True)[:2].print()
        Huge Giant Crab: H UA beast, 8.0CR DPR=25.6/20.2/13.5 161HP/14d12+70 15AC (walk 30, swim 30)
        Sperm Whale: G UA beast, 8.0CR DPR=20.9/18.7/13.2 189HP/14d20+42 13AC (walk 0, swim 60)
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

        >>> from legendlore import predicates as p
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
        Unseen Servant (rit.) A/60'/1h [V/S/M] (1:Bd+Wl+Wz)
        Flaming Sphere A/60'/C<=1m [V/S/M] (2:AAl+CLt+D+DW+S+WlC+Wz)
        Spirit Shroud B/S/C<=1m [V/S] (3:C+P+Wl+Wz)
        Elemental Bane A/90'/C<=1m [V/S] (4:A+D+Wl+Wz)
        Guardian of Faith A/30'/8h [V] (4:C+CLf+CLt+PCr+PD+WlC)
        Shadow of Moil A/S/C<=1m [V/S/M@150gp] (4:Wl)
        Sickening Radiance A/120'/C<=10m [V/S] (4:S+Wl+Wz)
        Wall of Fire A/120'/C<=1m [V/S/M] (4:AArt+CF+CLt+D+S+WlC+WlFi+Wz)
        Flame Strike A/60'/I [V/S/M] (5:C+CLt+CW+DW+PD+PG+WlC+WlFi+WlGe)
        Wall of Light A/120'/C<=10m [V/S/M] (5:S+Wl+Wz)
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

        >>> from legendlore import predicates as p
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

    def __add__(self, value):
        """Overrides list.__add__ to use the collection type when appropriate.

        >>> from repltools import m
        >>> enemies = m.where(name='Scout') + m.where(name='Orc Eye of Gruumsh') + m.where(name='Yorn')
        >>> type(enemies)
        <class 'legendlore.collection.Monsters'>
        >>> enemies += m.where(name='Bandit')
        >>> type(enemies)
        <class 'legendlore.collection.Monsters'>
        """
        ret = super().__add__(value)
        if type(self) == type(value):
            ret = type(self)(ret)
            if hasattr(self, 'name'):
                ret.name = self.name
        return ret

    def __mul__(self, value):
        """Similar to __add__.

        >>> from repltools import *
        >>> enemies = 4 * m.where(name='Scout')
        >>> type(enemies)  # Not sure if there is a way to make this work
        <class 'list'>
        >>> more_enemies = m.where(name='Bandit').set_name('badguise') * 4
        >>> type(more_enemies)
        <class 'legendlore.collection.Monsters'>
        >>> more_enemies.name
        'badguise'
        """
        ret = type(self)(super().__mul__(value))
        if hasattr(self, 'name'):
            ret.name = self.name
        return ret

    def set_name(self, newname):
        """Sets the `name` property of this collection and returns `self`."""
        self.name = newname
        return self

class Spells(Collection):
    """A list of spells from the db.

    If passed a list of spells, wraps it with formatting methods.
    If not, uses the full set of spells from the DB instead.
    """

    _xpath = '//spell'
    _type = db_items.Spell

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

    def __sub__(self, value):
        """Set-wise difference."""
        return type(self)(set(self) - set(value))

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
    Monster(Aarakocra: M NG humanoid (aarakocra), 1/4CR DPR=4.1/2.8/1.4 13HP/3d8 12AC (walk 20, fly 50))
    >>> monster('Duergar Warlord')
    Monster(Duergar Warlord: M LE humanoid (dwarf), 6.0CR DPR>=~8.6/6.2/3.8 75HP/10d8+30 20AC (walk 25))
    >>> monster('War Priest')
    Monster(War Priest: M Any alignment humanoid (any race), 9.0CR DPR=18.0/13.0/8.0 117HP/18d8+36 18AC (walk 30))
    >>> Monsters(m for m in Monsters() if getattr(m, 'name').startswith('C'))[0]
    Monster(Cambion: M Any Evil Alignment fiend, 5.0CR DPR>=~9.4/6.8/4.2 82HP/11d8+33 19AC (walk 30, fly 60))
    """
    _xpath = '//monster'
    _type = db_items.Monster

    def _post_process_where(self, result):
        """Sort by name and level."""
        return result.sorted('name').sorted('cr')

    def total_hp(self):
        return sum(m.hp for m in self)

    def weighted_ac(self):
        """Average AC of the group, weighted by the number of hp each monster has."""
        return round(sum(float(m.hp) * m.ac_num for m in self) / self.total_hp(), ndigits=1)

    def dpr(self, target_ac):
        """Average DPR of the entire group versus the target AC."""
        return round(careful_sum(m.dpr(target_ac) for m in self), ndigits=1)

    def combat_stats(self, target_ac):
        """Generates report of average/total combat stats vs `target_ac`.

        >>> from legendlore.repltools import m
        >>> from legendlore.collection import Monsters
        >>> enemies = m.where(name='Scout') + m.where(name='Orc Eye of Gruumsh') + m.where(name='Yorn')
        >>> enemies.combat_stats(16.5)
        {'dpr': 15.9, 'avg_ac': 13.3, 'weighted_ac': 13.8, 'hp': 93}
        """
        return dict({
            'dpr': self.dpr(target_ac),
            'avg_ac': round(float(sum(m.ac_num for m in self)) / len(self), ndigits=1),
            'weighted_ac': self.weighted_ac(),
            'hp': sum(m.hp for m in self),
            })

    def vs(self, opponents, weighted_ac=True):
        """Calculates combat stats for this set of monsters vs. another.

        Uses weighted average for AC calculations unless `weighted_ac` is false;
        in that case, uses regular average.

        >>> m = Monsters()
        >>> g1 = Monsters(m.where(name='Scout') + m.where(name='Orc Eye of Gruumsh') + m.where(name='Yorn'),
        ...               name='The Misfits')
        >>> g2 = m.where(name='Displacer Beast').set_name('The Holograms')
        >>> pprint(g1.vs(g2))
        {'The Misfits': {'weighted_ac': 13.8,
                         'avg_ac': 13.3,
                         'hp': 93,
                         'dpr': 22.2,
                         'ttv': 3.8},
         'The Holograms': {'weighted_ac': 13.0,
                           'avg_ac': 13.0,
                           'hp': 85,
                           'dpr': 9.9,
                           'ttv': 9.4}}
        """
        ac_calc = 'weighted_ac' if weighted_ac else 'avg_ac'

        defensive_stats = lambda group: {
            'weighted_ac': group.weighted_ac(),
            'avg_ac': round(float(sum(m.ac_num for m in group)) / len(group), ndigits=1),
            'hp': group.total_hp() }

        us = defensive_stats(self)
        them = defensive_stats(opponents)

        us['dpr'] = self.dpr(them.get(ac_calc))
        us['ttv'] = round(float(them['hp']) / us['dpr'], ndigits=1)
        them['dpr'] = opponents.dpr(us.get(ac_calc))
        them['ttv'] = round(float(us['hp']) / them['dpr'], ndigits=1)

        usname = getattr(self, 'name', 'group1')
        themname = getattr(opponents, 'name', 'group2')

        return {usname: us, themname: them}
