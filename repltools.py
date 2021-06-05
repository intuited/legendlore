"""repltools.py

A set of functions and objects intended to provide convenient access
to functionality commonly used in a REPL shell like ipython.

Can be sourced into the current REPL environment using ipython's %run command:

    %run -i /path/to/repltools.py

Functionality:
    #TODO
"""
from simpleeval import simple_eval
import re

class Blank:
    """Blank class used as basis for attribute-based structures."""
    None

import dnd5edb
from dnd5edb import predicates as p
s = dnd5edb.Spells()
m = dnd5edb.Monsters()

# Spell Print in a convenient format
sp = lambda name: s.search(name).print('xlist')

# convert Ability Score to Bonus
asbonus = lambda ascore: int((ascore - 10) / 2)

### just druid stuff

druid = Blank()
druid.__doc__ = """Functions and data structures pertinent to druids."""

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
druid.ac = Blank()
druid.ac.bearbarian = lambda creature: max(creature.ac_num if 'natural armor' in creature.ac.lower() else 0, asbonus(10 + creature.dex + creature.con))
druid.ac.bearbarian.__doc__ = 'Calculate AC for Druid/Barbarian wildshaped into `creature`.'
druid.ac.drunk = lambda creature, wis: max(creature.ac_num if 'natural armor' in creature.ac.lower() else 0, asbonus(10 + creature.dex + wis))
druid.ac.drunk.__doc__ = 'Calculate AC for Druid/Monk with Wisdom `wis` wildshaped into `creature`.'

### die roll stuff

prob = Blank()
prob.__doc__ = """Probability functionality."""

# average die roll calculations
def calc_avg(expression):
    """Calculates the average total of `expression`.

    `expression` can contain die-roll notation of the form [0-9]+d[0-9]+.

    >>> calc_avg('1')
    1
    >>> calc_avg('1 - 2')
    -1
    >>> calc_avg('1d4')
    2.5
    >>> calc_avg('1d10+5') # So anyway, I started blasting
    10.5
    >>> calc_avg('1d10+5 + 1d6') # I put a spell on you...
    14.0
    >>> calc_avg('2d10+10 + 2d6') # Level 5 at last
    28.0
    """
    #d_re = r'\b([0-9]+)d([0-9]+)\b'
    d_re = r'\b([0-9]+)d([0-9]+)\b'
    subbed = re.sub(d_re, r'(float(\1)*\2 + \1)/2', expression)
    return simple_eval(subbed)
prob.avg = calc_avg
del calc_avg

# die roll odds
prob.meetorbeat = lambda minimum: 1 - (float(minimum) - 1) / 20
prob.adv = lambda odds: 1 - ((1 - odds) * (1 - odds))
