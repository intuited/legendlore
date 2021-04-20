class Blank:
    """Blank class used as basis for attribute-based structures."""
    None

import dnd5edb
from dnd5edb import predicates as p
s = dnd5edb.Spells()
m = dnd5edb.Monsters()

# Spell Print in a convenient format
sp = lambda name: s.search(name).print('xlist')

### just druid stuff

# convert Ability Score to Bonus
asbonus = lambda ascore: int((ascore - 10) / 2)

def beasts(cr, fly=True, swim=True, crpred=p.lte):
    """Returns beast-type creatures matching the other conditions."""
    ret = m.where(type='beast', cr=crpred(cr))
    if not fly:
        ret = ret.where(speed=p.not_(p.in_('fly')))
    if not swim:
        ret = ret.where(speed=p.not_(p.in_('swim')))
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
