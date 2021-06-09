"""Digging into actions.

>>> from repltools import m, p
>>> from pprint import pprint
>>> from functools import partial
>>> pprint = partial(pprint, width=200)
>>> from collections import defaultdict
>>> from re import fullmatch

>>> have_ma = m.where(actions=p.contains('Multiattack'))
>>> have_ma[0]
Monster(Aberrant Spirit: M Unaligned aberration, --CR 40HP/-- 0AC (walk 30, fly 30))
>>> have_ma[0].actions.attack_form
ByHalfSpellLevel("The aberration makes a number of attacks equal to half this spell's level (rounded down).")

>>> def groupeddict(it):
...     d = defaultdict(list)
...     for k, v in it:
...         d[k].append(v)
...     return d
>>> histogram = lambda d: {k: len(v) for k, v in d.items()}

>>> have_actions = [n for n in m if hasattr(n, 'actions')]

>>> grouped_by_form = groupeddict(n.actions.attack_form.summary for n in have_actions)
>>> histogram(grouped_by_form)
{'ByHalfSpellLevel': 9, 'Named': 248, 'Default': 323, 'AnyMelee': 107, 'WithNamed2Options': 14, 'ArtAAndArtB': 204, 'ArtAAndArtBOrC': 21, 'AOrB': 20, 'WithNamed': 54, 'MeleeOrRanged': 28, 'Any': 15, 'AttacksWithNamed': 27, 'MakesAAndB': 6, 'TwiceArtAAndArtB': 6, 'NamedAndUses': 4}

>>> pprint(grouped_by_form['Default'][:40])
>>> #pprint(grouped_by_form['ByHalfSpellLevel'][:40])
"""
