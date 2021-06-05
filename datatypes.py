"""Various items of data used by both parse.py and higher level code."""
from functools import total_ordering
from logging import warning
from collections import namedtuple

@total_ordering
class OrderedField:
    """Base class for fields which have a predefined set of values with a predefined order.

    Also provides abbreviation functionality.
    """
    def __init__(self, value):
        """Attempt to remap the value if it's not in our known value set.

        >>> SpellRange('Self (10-foot sphere)')
        SpellRange('Self (10-foot-radius sphere)')
        >>> SpellRange('Total gibberish.') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        KeyError: "SpellRange: unknown value 'Total gibberish.' could not be instantiated."
        """
        if value in self._value_aliases:
            value = self._value_aliases[value]
        if value not in self._values:
            raise KeyError(f'{type(self).__name__}: unknown value {repr(value)} could not be instantiated.')
        self.value = value

    def __repr__(self):
        """Make it look offical.

        >>> SpellRange('90 feet')
        SpellRange('90 feet')
        """
        return f'{type(self).__name__}({repr(self.value)})'
    def __str__(self):
        """Just converts the underlying data to a string.

        This is apparently Not The Way you're supposed to handle this, but it seems like it should work.

        >>> str(SpellRange('90 feet'))
        '90 feet'
        """
        return str(self.value)

    def __eq__(self, other):
        """`True` if this range is equal to `other`.

        `other` can be either another SpellRange object
        or a value of a type compatible with that of self.value.
        
        >>> SpellRange('Self') == SpellRange('Self')
        True
        >>> SpellRange('Self') == 'Self'
        True
        >>> SpellRange('Self') == 'Self (10-foot radius)'
        False
        """
        if type(other) is not SpellRange:
            other = SpellRange(other)
        return self._ord() == other._ord()

    def __lt__(self, other):
        """`True` if this range is lower in the sort order than `other`.

        `other` can be either another SpellRange object
        or a value of a type compatible with that of self.value.

        >>> SpellRange('Touch') < SpellRange('60 feet')
        True
        >>> SpellRange('15 feet') < SpellRange('Self (15-foot cone)')
        False
        >>> SpellRange('Self (60-foot cone)') < 'Touch'
        True
        """
        if type(other) is not SpellRange:
            other = SpellRange(other)
        return self._ord() < other._ord()

    def abbr(self):
        """Returns the abbreviation used for this range in one-line descriptions."""
        return self._values[self.value]

    def _ord(self):
        """Returns the ordinal position of this range in the full set of ranges.

        Used by rich comparison methods.

        >>> SpellRange('Self')._ord()
        1
        >>> SpellRange('90 feet')._ord()
        26
        """
        for i, r in enumerate(self._values.keys()):
            if r == self.value:
                return i
        raise ValueError(f'SpellRange._ord: self.value "{self.value}" not found in self._values')

class SpellRange(OrderedField):
    """Ordered set of all ranges and their abbreviated form."""
    _values = {
        None: "N",
        'Self': 'S',
        "Self (5-foot radius)": "S(5'r)",
        'Self (10-foot radius)': "S(10'r)",
        'Self (10-foot-radius sphere)': "S(10'r-sphere)",
        'Self (10-foot-radius hemisphere)': "S(10'r-hemisphere)",
        "Self (15-foot radius)": "S(15'r)",
        'Self (15-foot cone)': "S(15'cone)",
        'Self (15-foot cube)': "S(15'cube)",
        'Self (30-foot radius)': "S(30'r)",
        'Self (30-foot cone)': "S(30'cone)",
        "Self (30-foot line)": "S(30'line)",
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
        "20 feet": "20'",
        '30 feet': "30'",
        '60 feet': "60'",
        '90 feet': "90'",
        '100 feet': "100'",
        '120 feet': "120'",
        '150 feet': "150'",
        '300 feet': "300'",
        '500 feet': "500'",
        "1000 feet": "1000'",
        '1 mile': "1mi",
        '500 miles': "500mi",
        'Unlimited': "Unlimited"}

    _value_aliases = {
        "Self (10-foot sphere)": "Self (10-foot-radius sphere)",
        "Self (15-foot-radius)": "Self (15-foot radius)",
        "Self (10-foot hemisphere)": "Self (10-foot-radius hemisphere)",
        }

class CastingTime(OrderedField):
    _values = {
        '1 reaction': 'R',
        '1 reaction, which you take when you take acid, cold, fire, lightning, or thunder damage': 'R*',
        '1 reaction, which you take when a humanoid you can see within 60 feet of you dies': 'R*',
        '1 bonus action': 'B',
        '1 action': 'A',
        'part of the Attack action to fire a magic arrow': 'A*',
        '1 minute': '1m',
        '10 minutes': '10m',
        '1 hour': '1h',
        '8 hours': '8h',
        '1 action or 8 hours': 'A/8h',
        '1 action, 8 hours': 'A/8h',
        '12 hours': '12h',
        '24 hours': '24h'}
    _value_aliases = {
        '1 action, 8 hours': '1 action or 8 hours',
        }

class SpellDuration(OrderedField):
    """Spell durations mapped to their abbreviations.

    Abbreviations include:
    S (special), 1r (1 round), 1m, 1h, <=1h
    """
    _values = {
        'Instantaneous': 'I',
        'Instantaneous or 1 hour (see below)': 'I/1h',
        'Special': "S",
        '1 turn': '1t',
        'up to 1 round': '<=1r',
        '1 round': '1r',
        'up to 6 rounds': '<=6r',
        'Up to 1 minute': '<=1m',
        '1 minute': '1m',
        'up to 10 minutes': "<=10m",
        '10 minutes': '10m',
        'Up to 1 hour': '<=1h',
        '1 hour': "1h",
        'up to 2 hours': '<=2h',
        '6 hours': '6h',
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
        'Until dispelled': "UD",
        'special': 'S',
        }
    _value_aliases = {
        'up to 1 hour': 'Up to 1 hour',
        'up to 8 hours': 'Up to 8 hours',
        'up to 1 minute': 'Up to 1 minute',
        }

# Maps caster classes as found in <spell> tags to abbreviations used in one-line descriptions.
# Abbreviations are subject to change as ambiguities are introduced with new class archetypes.
# Doesn't need to subclass OrderedField because alphabetical order works just fine.
caster_classes = {
    'Artificer': "A",
    'Artificer (Alchemist)': 'AAl',
    'Artificer (Armorer)': "AArm",
    'Artificer (Artillerist)': "AArt",
    'Artificer (Battle Smith)': "ABS",
    'Bard': "Bd",
    'Bard (Glamour)': 'BdG',
    'Barbarian': 'Bb',
    'Barbarian (Ancestral Guardian)': 'BbAG',
    'Barbarian (Totem Warrior)': 'BbTW',
    'Cleric': "C",
    'Cleric (Arcana)': "CA",
    'Cleric (Death)': "CD",
    'Cleric (Forge)': "CF",
    'Cleric (Grave)': "CG",
    'Cleric (Knowledge)': "CK",
    'Cleric (Life)': "CLf",
    'Cleric (Light)': "CLt",
    'Cleric (Nature)': "CN",
    'Cleric (Order)': "CO",
    'Cleric (Protection)': "CPr",
    'Cleric (Peace)': "CPe",
    'Cleric (Tempest)': "CTm",
    'Cleric (Twilight)': "CTw",
    'Cleric (Trickery)': "CTr",
    'Cleric (War)': "CW",
    'Druid': "D",
    'Druid (Arctic)': "DLA",
    'Druid (Coast)': "DLC",
    'Druid (Desert)': "DLD",
    'Druid (Forest)': "DLF",
    'Druid (Grassland)': "DLG",
    'Druid (Mountain)': "DLM",
    'Druid (Swamp)': "DLS",
    'Druid (Underdark)': "DLU",
    'Druid (Land)': "DL",
    'Druid (Moon)': "DM",
    'Druid (Spores)': "DS",
    'Druid (Wildfire)': "DW",
    'Eldritch Invocations': "EI",
    'Fighter': "F",
    'Fighter (Arcane Archer)': "FAA",
    'Fighter (Battle Master)': "FBM",
    'Fighter (Eldritch Knight)': "FEK",
    'Martial Adept': "MA",
    'Monk': "M",
    'Monk (Way of the Four Elements)': "M4",
    'Paladin': "P",
    'Paladin (Ancients)': "PA",
    'Paladin (Conquest)': "PCo",
    'Paladin (Crown)': "PCr",
    'Paladin (Devotion)': "PD",
    'Paladin (Glory)': "PG",
    'Paladin (Oathbreaker)': "PO",
    'Paladin (Redemption)': "PR",
    'Paladin (Treachery)': "PT",
    'Paladin (Vengeance)': "PV",
    'Paladin (Watchers)': "PW",
    'Ranger': "Ra",
    'Ranger (Fey Wanderer)': "RaFW",
    'Ranger (Gloom Stalker)': "RaGS",
    'Ranger (Horizon Walker)': "RaHW",
    'Ranger (Monster Slayer)': "RaMS",
    'Ranger (Primeval Guardian)': "RaPG",
    'Ranger (Swarmkeeper)': "RaS",
    'Ranger (No Spells)': "Ra",
    'Ritual Caster': "Rit",
    'Rogue': "Ro",
    'Rogue (Arcane Trickster)': "RoAT",
    'Sorcerer': "S",
    'Sorcerer (Aberrant Mind)': "SAM",
    'Sorcerer (Clockwork Soul)': "SCS",
    'Sorcerer (Divine Soul)': "SDS",
    'Sorcerer (Shadow)': "SSh",
    'Sorcerer (Stone Sorcery)': "SSS",
    'Warlock': "Wl",
    'Warlock (Archfey)': "WlA",
    'Warlock (Celestial)': "WlC",
    'Warlock (Fathomless)': "WlFa",
    'Warlock (Fiend)': "WlFi",
    'Warlock (Genie)': "WlGe",
    'Warlock (Great Old One)': "WlGOO",
    'Warlock (Hexblade)': "WlH",
    'Warlock (Raven Queen)': "WlR",
    'Warlock (Seeker)': "WlS",
    'Warlock (Undying)': "WlU",
    'Wizard': "Wz",
    'Wizard (Chronurgy)': "WzC",
    'Wizard (Graviturgy)': "WzG",
    'Wizard (Illusion)': "WzI",
    }


# damage types as they are used in the XML file
# for resistances, vulnerabilities, and immunities
damage_types = { # simple types which don't need remapping
    'bludgeoning', 'piercing', 'slashing',
    'poison', 'acid', 'fire', 'cold', 'radiant', 'necrotic',
    'lightning', 'thunder', 'force', 'psychic',

    'charmed', 'petrified', 'blinded', # should be in conditions but the DB is wrong

    'damage from spells',
    'piercing from magic weapons wielded by good creatures',
    "one of the following: acid, cold, fire, lightning or poison",
    "one of the following: acid, cold, fire, lightning, or poison",
}
damage_mappings = { # translation of complex expressions and simple expressions compounded with commas
    'bludgeoning, piercing, and slashing from nonmagical attacks': {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning, piercing, and slashing damage from nonmagical weapons": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning, piercing, slashing from nonmagical attacks": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning, piercing, and slashing damage from nonmagical attacks": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical weapons": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning, piercing and slashing from nonmagical attacks": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning, piercing, and slashing that is nonmagical": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "bludgeoning from nonmagical attacks": {
        'types': {
            'nonmagical bludgeoning'}},

    "fire, bludgeoning, piercing, and slashing from nonmagical attacks": {
        'types': {
            'nonmagical fire',
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},
    "cold, fire, lightning, bludgeoning, piercing and slashing that is nonmagical": {
        'types': {
            'nonmagical cold',
            'nonmagical fire',
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'}},

    'non magical bludgeoning, piercing, and slashing (from stoneskin)': {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'},
        'notes': {
            'from stoneskin': [
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing']}},
    "nonmagical bludgeoning, piercing, slashing (from stoneskin)": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'},
        'notes': {
            'from stoneskin': [
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing']}},
    "nonmagical bludgeoning, piercing, slashing (from stoneskin), poison": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing',
            'poison'},
        'notes': {
            'from stoneskin': [
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing']}},
    "nonmagical bludgeoning, piercing, slashing (from stoneskin), fire": {
        'types': {
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing',
            'fire'},
        'notes': {
            'from stoneskin': [
                'nonmagical bludgeoning',
                'nonmagical piercing',
                'nonmagical slashing']}},

    "bludgeoning, piercing, and slashing from nonmagical attacks that aren't silvered": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical attacks that aren’t silvered": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, slashing from nonmagical attacks that aren't silvered": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical/nonsilver weapons": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical attacks not made with silvered weapons": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical weapons that aren't silvered": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, and slashing damage from nonmagical attacks that aren't silvered": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, and slashing damage from nonmagical attacks that aren't silvered weapons": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},
    "bludgeoning, piercing, slashing from nonmagical attacks not made with silvered weapons": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},

    "slashing damage from nonmagical attacks not made with silvered weapons": {
        'types': {
            'nonmagical nonsilver slashing'}},
    "slashing from nonmagical attacks not made with silvered weapons": {
        'types': {
            'nonmagical nonsilver slashing'}},

    "bludgeoning, piercing, slashing from nonmagical attacks that aren't adamantine or silvered": {
        'types': {
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},

    "lightning, poison, bludgeoning, piercing, sand slashing from non-magical attacks that aren't adamantine or silvered": {
        'types': {
            'lightning',
            'poison',
            'nonmagical nonsilver bludgeoning',
            'nonmagical nonsilver piercing',
            'nonmagical nonsilver slashing'}},

    "bludgeoning, piercing, and slashing from nonmagical attacks that aren't adamantine": {
        'types': {
            'nonmagical nonadamantine bludgeoning',
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "bludgeoning, piercing, and slashing damage from nonmagical attacks not made with adamantine weapons": {
        'types': {
            'nonmagical nonadamantine bludgeoning',
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "bludgeoning, piercing, slashing from nonmagical attacks that aren't adamantine": {
        'types': {
            'nonmagical nonadamantine bludgeoning',
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical attacks that aren’t adamantine": {
        'types': {
            'nonmagical nonadamantine bludgeoning',
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "bludgeoning, piercing, and slashing from nonmagical weapons that aren't adamantine": {
        'types': {
            'nonmagical nonadamantine bludgeoning',
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "bludgeoning, piercing, slashing from nonmagical attacks not made with adamantine weapons": {
        'types': {
            'nonmagical nonadamantine bludgeoning',
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "piercing, slashing from nonmagical attacks that aren't adamantine": {
        'types': {
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},
    "piercing and slashing from nonmagical attacks that aren't adamantine": {
        'types': {
            'nonmagical nonadamantine piercing',
            'nonmagical nonadamantine slashing'}},

    "fire, bludgeoning, piercing, and slashing from metal weapons": {
        'types': {
            'fire',
            'metal bludgeoning',
            'metal piercing',
            'metal slashing'}},

    "bludgeoning, piercing, and slashing from magic weapons": {
        'types': {
            'magical bludgeoning',
            'magical piercing',
            'magical slashing'}},
     "bludgeoning, piercing, slashing from magic weapons": {
        'types': {
            'magical bludgeoning',
            'magical piercing',
            'magical slashing'}},

    "bludgeoning, piercing, and slashing while in dim light or darkness": {
        'types': {
            'bludgeoning while in dim light or darkness',
            'piercing while in dim light or darkness',
            'slashing while in dim light or darkness'}},
    "bludgeoning, piercing, slashing while in dim light or darkness": {
        'types': {
            'bludgeoning while in dim light or darkness',
            'piercing while in dim light or darkness',
            'slashing while in dim light or darkness'}},
    "bludgeoning, piercing, and slashing from nonmagical attacks while in dim light or darkness": {
        'types': {
            'nonmagical bludgeoning while in dim light or darkness',
            'nonmagical piercing while in dim light or darkness',
            'nonmagical slashing while in dim light or darkness'}},
    "bludgeoning, piercing, slashing from nonmagical attacks while in dim light or darkness": {
        'types': {
            'nonmagical bludgeoning while in dim light or darkness',
            'nonmagical piercing while in dim light or darkness',
            'nonmagical slashing while in dim light or darkness'}},

    "bludgeoning, piercing, slashing from metal weapons": {
        'types': {
            'bludgeoning from metal weapons',
            'piercing from metal weapons',
            'slashing from metal weapons'}},

    "while wearing the mask of the dragon queen: acid, cold, lightning, poison": {
        'types': {
            'acid', 'cold', 'lightning', 'poison',
            'nonmagical bludgeoning',
            'nonmagical piercing',
            'nonmagical slashing'},
        'notes': {
            'While wearing the mask of the Dragon Queen': [
                'acid', 'cold', 'lightning', 'poison']}},
    "while wearing the mask of the dragon queen: fire": {
        'types': {'fire'},
        'notes': {'while wearing the mask of the dragon queen': 'fire'}},

    "cold (while wearing the ring of winter)": {
        'types': {'cold'},
        'notes': {'while wearing the ring of winter': 'cold'}},
    "while wearing the ring of winter: cold": {
        'types': {'cold'},
        'notes': {'while wearing the ring of winter': 'cold'}},

    'posion': {
        'types': {'poison'}},

    # Elemental Spirit damage types from the Summon Elemental spell in TCoE
    "lightning, thunder (air only), piercing": {    # this seems to be a mistranscription: this "piercing" is absent from the stat block in TCoE.
        'types': {'lightning', 'thunder'},
        'notes': {'air form only': ['lightning', 'thunder']}},
    "piercing, slashing (earth only)": {
        'types': {'piercing', 'slashing'},
        'notes': {'earth form only': ['piercing, slashing']}},
    "acid (water only)": {
        'types': {'acid'},
        'notes': {'water form only': 'acid'}},
    "fire (fire only)": {
        'types': {'fire'},
        'notes': {'fire form only': 'fire'}},

    # choose-one damage types from Rise of Tiamat
    "one of the following: acid, cold, fire, lightning, poison": {
        'types': {'acid', 'cold', 'fire', 'lightning', 'poison'},
        'notes': {'choose one from acid, cold, fire, lightning, poison': ['acid', 'cold', 'fire', 'lightning', 'poison']}},
    "one of the following: acid, cold, fire, lightning, poison, poison": {  # not sure what happened here
        'types': {'acid', 'cold', 'fire', 'lightning', 'poison'},
        'notes': {'choose one from acid, cold, fire, lightning, poison': ['acid', 'cold', 'fire', 'lightning', 'poison']}},

    # Halaster Blackcloak from Waterdeep: Dungeon of the Mad Mage
    'lightning (granted by the blast scepter, see "special equipment" below)': {
        'types': {'lightning'},
        'notes': {'granted by the blast scepter': 'lightning'}},
}

class ReversibleDict(dict):
    """Dictionary type for one-to-one mappings."""
    def reverse_lookup(self, v):
        """Returns the key whose value equals `v`.

        >>> rd = ReversibleDict({1: 'one', 2: 'two'})
        >>> rd.reverse_lookup('one')
        1
        >>> rd.reverse_lookup('two')
        2
        """
        for key, value in self.items():
            if value == v:
                return key

schools = ReversibleDict({
    "Evocation": 'EV',
    "Transmutation": 'T',
    "Conjuration": 'C',
    "Abjuration": 'A',
    "Enchantment": 'EN',
    "Divination": 'D',
    "Necromancy": 'N',
    "Illusion": 'I',
    None: None})

sources = {
    'Acquisitions Incorporated': 'ai',
    "Elemental Evil Player's Companion": 'eepc',
    "Guildmasters' Guide to Ravnica": 'ggtr',
    'Lost Laboratory of Kwalish': 'llok',
    "Player's Handbook": 'phb',
    'Princes of the Apocalypse': 'pota',
    "Sword Coast Adventurer's Guide": 'scag',
    "Volo's Guide to Monsters": 'vgm',
    "Xanathar's Guide to Everything": 'xgte',
    "Explorer's Guide to Wildemount": 'egtw',
    "Wayfinder's Guide to Eberron": 'wgte',
    "Eberron: Rising from the Last War": 'erftlw',
    'Mythic Odysseys of Theros': 'moot',
    "Icewind Dale: Rime of the Frostmaiden": 'rotf',
    "Tasha's Cauldron of Everything": 'tcoe',
    }

# `Reference` tuple used by Spell class
Reference = namedtuple('Reference', ('book', 'page'))

# Exceptional spell components fields which we parse manually.
# This includes
# - components including multiple monetary values
# - components in which the string "consume" occurs but for which no components with monetary value are consumed
# - components which use the word "each" to multiply the given monetary value
components_exceptions = {
    "a pinch of salt and one copper piece placed on each of the corpse's eyes, which must remain there for the duration":
        {'used': 0.01},
    'a diamond worth at least 1,000 gp and at least 1 cubic inch of flesh of the creature that is to be cloned, which the spell consumes, and a vessel worth at least 2,000 gp that has a sealable lid and is large enough to hold a Medium creature, such as a huge urn, coffin, mud-filled cyst in the ground, or crystal container filled with salt water':
        {'consumed': 1000, 'used': 2000},
    'a miniature portal carved from ivory, a small piece of polished marble, and a tiny silver spoon, each item worth at least 5 gp':
        {'used': 15},
    'a pair of platinum rings worth at least 50 gp each, which you and the target must wear for the duration':
        {'used': 100},
    'a vial of quicksilver worth 500 gp and a life-sized human doll, both of which the spell consumes, and an intricate crystal rod worth at least 1,500 gp that is not consumed':
        {'consumed': 500, 'used': 1500},
    'an exquisite chest, 3 feet by 2 feet by 2 feet, constructed from rare materials worth at least 5,000 gp, and a Tiny replica made from the same materials worth at least 50 gp':
        {'used': 5050},
    'clay, ash, and mandrake root, all of which the spell consumes, and a jewel-encrusted dagger worth at least 1,000 gp':
        {'used': 1000},
    'for each creature you affect with this spell, you must provide one jacinth worth at least 1,000 gp and one ornately carved bar of silver worth at least 100 gp, all of which the spell consumes':
        {'consumed': 1100},
    'incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each':
        {'consumed': 250, 'used': 200},
    'one clay pot filled with grave dirt, one clay pot filled with brackish water, and one 150 gp black onyx stone for each corpse':
        {'used': 150},
    'seven sharp thorns or seven small twigs, each sharpened to a point':
        {},
    }
