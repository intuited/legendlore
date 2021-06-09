"""Digging into actions.

How many of each form do we find?
>>> have_actions = [n for n in m if hasattr(n, 'actions')]
>>> grouped_by_form = groupeddict(n.actions.attack_form.summary for n in have_actions)
>>> h = histogram(grouped_by_form)
{'NoMultiattack': 1017, 'Named': 248, 'Default': 323, 'AnyMelee': 107, 'ArtAAndArtB': 204, 'ArtAAndArtBOrC': 21, 'WithNamed': 54, 'AOrB': 20, 'Any': 15, 'MeleeOrRanged': 28, 'NamedAndUses': 4, 'AttacksWithNamed': 27, 'WithNamed2Options': 14, 'MakesAAndB': 6, 'TwiceArtAAndArtB': 6, 'ByHalfSpellLevel': 9}

Sorted by frequency:
>>> pprint(dict(sorted(h.items(), key=lambda tup: tup[1], reverse=True)))
{'NoMultiattack': 1017,
 'Default': 323,
 'Named': 248,
 'ArtAAndArtB': 204,
 'AnyMelee': 107,
 'WithNamed': 54,
 'MeleeOrRanged': 28,
 'AttacksWithNamed': 27,
 'ArtAAndArtBOrC': 21,
 'AOrB': 20,
 'Any': 15,
 'WithNamed2Options': 14,
 'ByHalfSpellLevel': 9,
 'MakesAAndB': 6,
 'TwiceArtAAndArtB': 6,
 'NamedAndUses': 4}

Sorted by attack form declaration order:
>>> pprint(sorted_dict(h, key_by_attack_form_pos))
{'Any': 15,
 'AnyMelee': 107,
 'MeleeOrRanged': 28,
 'Named': 248,
 'WithNamed': 54,
 'WithNamed2Options': 14,
 'NamedAndUses': 4,
 'AttacksWithNamed': 27,
 'ArtAAndArtBOrC': 21,
 'ArtAAndArtB': 204,
 'TwiceArtAAndArtB': 6,
 'MakesAAndB': 6,
 'AOrB': 20,
 'NoMultiattack': 1017,
 'ByHalfSpellLevel': 9,
 'Default': 323}

Total monsters handled:
>>> total = sum(count for form, count in h.items())
>>> f'{total - h["Default"]}/{total} == {round(float(total - h["Default"]) / total * 100, 2)}%'
'1780/2103 == 84.64%'

What do the still-unhandled cases look like?
>>> pprint(grouped_by_form['Default'][:40])

[Uncomment for info on a specific case]
>>> #pprint(grouped_by_form['ByHalfSpellLevel'][:40])
"""
from dnd5edb.repltools import m, p
from functools import partial
from collections import defaultdict
from pprint import pprint
pprint = partial(pprint, width=200, sort_dicts=False)
from re import fullmatch
import itertools
from dnd5edb import actions

def groupeddict(it):
    d = defaultdict(list)
    for k, v in it:
        d[k].append(v)
    return d
histogram = lambda d: {k: len(v) for k, v in d.items()}

form_pos = dict(zip(actions.attack_forms.values(), itertools.count()))
"""Sorts the histogram by the position of the labeled form in actions.attack_forms"""
def key_by_attack_form_pos(tup):
    label, count = tup
    cls = getattr(actions, label)
    return form_pos[cls]

def sorted_dict(d, key):
    return dict(sorted(d.items(), key=key))
