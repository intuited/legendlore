from simpleeval import simple_eval
import re

class Blank:
    """Blank class used as basis for attribute-based structures."""
    None

import dnd5edb
from dnd5edb import predicates as p
s = dnd5edb.Spells()
m = dnd5edb.Monsters()

# quick Spell Print in commonly used formats
sp = lambda name: s.search(name).print('xlist')
pl = lambda name: s.search(name).print('plop')

### just druid stuff

# convert Ability Score to Bonus
asbonus = lambda ascore: int((ascore - 10) / 2)

def beasts(cr, fly=True, swim=True, crpred=p.lte):
    """Returns beast-type creatures matching the other conditions."""
    ret = m.where(type='beast', cr=crpred(cr))
    if not fly:
        ret = ret.where(speed=p.not_(p.contains('fly')))
    if not swim:
        ret = ret.where(speed=p.not_(p.contains('swim')))
    return ret

# moon druid wildshape options at various levels
elementals = ['Air Elemental', 'Earth Elemental', 'Fire Elemental', 'Water Elemental']
elementals = m.where(name=lambda attr, obj: getattr(obj, attr, '') in elementals)
moonws = {
    2:  beasts(1, swim=False, fly=False),
    4:  beasts(1, swim=True, fly=False),
    6:  beasts(2, swim=True, fly=False),
    8:  beasts(2, swim=True, fly=True),
    9:  beasts(3, swim=True, fly=True),
    10: beasts(3, swim=True, fly=True).extend(elementals),
    12: beasts(4, swim=True, fly=True).extend(elementals),
    15: beasts(5, swim=True, fly=True).extend(elementals),
    18: beasts(6, swim=True, fly=True).extend(elementals), }
moonws = { k: v.sorted('cr') for k, v in moonws.items() }

# AC evaluation for druid mc
bearbarian_ac = lambda c: max(c.ac_num if 'natural armor' in c.ac.lower() else 0, asbonus(10 + c.dex + c.con))
drunk_ac = lambda c, wis: max(c.ac_num if 'natural armor' in c.ac.lower() else 0, asbonus(10 + c.dex + wis))

# average die roll calculations
def calc_avg(expression):
    """Calculates the average total of `expression`.

    `expression can contain die-roll notation of the form [0-9]+d[0-9]+.

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

# die roll odds
meetorbeat = lambda minimum: 1 - (float(minimum) - 1) / 20
adv = lambda odds: 1 - ((1 - odds) * (1 - odds))
