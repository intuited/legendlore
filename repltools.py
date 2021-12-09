"""repltools.py

A set of functions and objects intended to provide convenient access
to functionality commonly used in a REPL shell like ipython.

Can be sourced into the current REPL environment using ipython's %run command:

    %run -i /path/to/repltools.py

Functionality:
    #TODO

>>> bb = m.where(name='Brown Bear')[0]
>>> druid.ac.bearbarian(bb) # AC for wildshaped Druid/Barbarian
13
>>> druid.ac.drunk(bb, 18) # AC for wildshaped Druid/Monk with 18 WIS
14
"""
from dnd5edb import collection, calc
from dnd5edb import predicates as p
from dnd5edb.util import Generic

# quick Spell Print in commonly used formats
sp = lambda name: s.search(name).print('xlist')
pl = lambda name: s.search(name).print('plop')

# just imported so they'll be available in the REPL
from dnd5edb.db_items import Monster, Spell
from dnd5edb.collection import Monsters, Spells

from dnd5edb.datatypes import SpellRange

# generally useful routines
from pprint import pprint
from functools import partial
pp = partial(pprint, sort_dicts=False)
del pprint
from copy import deepcopy

# Quick-access abbreviations
s = Spells()
s.byclass = Generic(**{cls.lower(): s.where(classes=p.contains(cls))
                       for cls in ['Artificer', 'Bard', 'Cleric', 'Druid', 'Paladin', 'Ranger', 'Sorcerer', 'Wizard', 'Warlock']})
s.byclass.dss = Spells(set(s.byclass.sorcerer + s.byclass.cleric))  # Divine Soul Sorcerer
m = Monsters()

def a(x, p=1):
    """Average of XdY calculation, rounded to `p` digits."""
    return round(calc.avg(x), ndigits=p)

# convert Ability Score to Bonus
asbonus = lambda ascore: int((ascore - 10) / 2)

### just druid stuff

druid = Generic(__doc__="Functions and data structures pertinent to druids.")

def beasts(cr, fly=True, swim=True, crpred=p.lte):
    """Returns beast-type creatures matching the other conditions.

    `crpred` is a predicate factory from `dnd5edb.predicates`.
    It's passed `cr` and the returned function is used to filter results
    based on the creature CR.
    """
    ret = m.where(type='beast', cr=crpred(cr))
    if not fly:
        ret = ret.where(speed=p.not_(p.contains('fly')))
    if not swim:
        ret = ret.where(speed=p.not_(p.contains('swim')))
    return ret
druid.beasts = beasts

# moon druid wildshape options at various levels
elementals = ['Air Elemental', 'Earth Elemental', 'Fire Elemental', 'Water Elemental']
elementals = m.where(name=p.in_(elementals))
druid.moonws = {
    2:  beasts(1, swim=False, fly=False),
    4:  beasts(1, swim=True, fly=False),
    6:  beasts(2, swim=True, fly=False),
    8:  beasts(2, swim=True, fly=True),
    9:  beasts(3, swim=True, fly=True),
    10: beasts(3, swim=True, fly=True).extend(elementals),
    12: beasts(4, swim=True, fly=True).extend(elementals),
    15: beasts(5, swim=True, fly=True).extend(elementals),
    18: beasts(6, swim=True, fly=True).extend(elementals), }
del beasts
del elementals
druid.moonws = { k: v.sorted('cr') for k, v in druid.moonws.items() }

# AC evaluation for druid mc
druid.ac = Generic()
druid.ac.bearbarian = lambda creature: max(creature.ac_num if 'natural armor' in creature.ac[0].lower() else 0, asbonus(10 + creature.dex + creature.con))
druid.ac.bearbarian.__doc__ = 'Calculate AC for Druid/Barbarian wildshaped into `creature`.'
druid.ac.drunk = lambda creature, wis: max(creature.ac_num if 'natural armor' in creature.ac[0].lower() else 0, asbonus(10 + creature.dex + wis))
druid.ac.drunk.__doc__ = 'Calculate AC for Druid/Monk with Wisdom `wis` wildshaped into `creature`.'

def reload_db():
    """Reloads the database and refreshes code related to it."""
    ##~~ from dnd5edb.parse import XML
    ##~~ from importlib import reload
    ##~~ del Monsters._parsed
    ##~~ del Spells._parsed
    ##~~ from dnd5edb import repltools
    ##~~ repltools.Monsters = collection.Monsters
    ##~~ repltools.m = Monsters()
    ##~~ repltools.s = Spells()
    ##~~ XML.tree = None

    from importlib import reload
    from dnd5edb import parse, predicates, db_items, actions, collection, repltools
    reload(parse)
    reload(predicates)
    reload(db_items)
    reload(actions)
    reload(collection)
    reload(repltools)
