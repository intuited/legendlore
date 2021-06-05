r"""spell_nodes.py

Similar to monster_nodes: provides analysis of <spell> nodes in the xml database.

Pull the tree data, select spells from the tree
>>> tree = parse.XML.get_tree()
>>> spells = tree.xpath('//spell')

All string tags of spell nodes
>>> string_tags(subnode_tags(spells))
['classes', 'components', 'duration', 'level', 'name', 'range', 'ritual', 'roll', 'school', 'text', 'time']

There are 257 unique components strings
>>> components = tree.xpath('//spell/components')
>>> components = sorted(set(c.text for c in components))
>>> len(components)
257

They look like this
>>> jprint(components[:10])
S
S, M (25 feet of rope, which the spell consumes)
S, M (a bit of fleece)
S, M (a coin), R
S, M (a drop of water or piece of ice)
S, M (a glowing stick of incense or a crystal vial filled with phosphorescent material)
S, M (a lead-based ink worth at least 10 gp, which the spell consumes)
S, M (a melee weapon worth at least 1 sp)
S, M (a pinch of sand)
S, M (a small amount of makeup applied to the face as this spell is cast)

With the details of material components removed, there are only 8 unique strings
>>> simplify_m = partial(re.sub, re_components, 'M')
>>> material_details_removed = sorted(set(simplify_m(c) for c in components))
>>> jprint(material_details_removed)
S
S, M
S, M, R
V
V, M
V, S
V, S, M
V, S, R

What do the material components with monetary value look like?
>>> hasm = lambda c: re.search(re_components, c)
>>> havem = [c for c in components if hasm(c)]
>>> havev = [c for c in havem if re.search('[0-9]', c)]
>>> jprint(havev[:6])
S, M (25 feet of rope, which the spell consumes)
S, M (a lead-based ink worth at least 10 gp, which the spell consumes)
S, M (a melee weapon worth at least 1 sp)
V, M (a melee weapon worth at least 1 sp)
V, M (rare chalks and inks infused with precious gems worth 50 gp, which the spell consumes)
V, S, M (10 gp worth of charcoal, incense, and herbs that must be consumed by fire in a brass brazier)

Components containing containing numerals that don't indicate monetary value:
We avoid false positives here by checking for /[gs]p/ or "gold pieces" afterwards
>>> havev_nomatch = [c for c in havev if not re.search(re_value, c)]
>>> jprint(havev_nomatch)
S, M (25 feet of rope, which the spell consumes)
V, S, M (a vial of blood from a humanoid killed within the past 24 hours)

Are there any that use the string "consume" that don't consume their components?
This should be checked with each update for new exceptions that require custom handlers
>>> jprint(c for c in havem if c.find('consume') > -1)
S, M (25 feet of rope, which the spell consumes)
S, M (a lead-based ink worth at least 10 gp, which the spell consumes)
V, M (rare chalks and inks infused with precious gems worth 50 gp, which the spell consumes)
V, S, M (10 gp worth of charcoal, incense, and herbs that must be consumed by fire in a brass brazier)
V, S, M (25 gold pieces, or mineral goods of equivalent value, which the spell consumes)
V, S, M (25 gp worth of powdered silver, which the spell consumes)
V, S, M (a diamond worth at least 1,000 gp and at least 1 cubic inch of flesh of the creature that is to be cloned, which the spell consumes, and a vessel worth at least 2,000 gp that has a sealable lid and is large enough to hold a Medium creature, such as a huge urn, coffin, mud-filled cyst in the ground, or crystal container filled with salt water)
V, S, M (a diamond worth at least 1,000 gp, which the spell consumes)
V, S, M (a diamond worth at least 500 gp, which the spell consumes)
V, S, M (a gem-encrusted bowl worth at least 1,000 gp, which the spell consumes)
V, S, M (a jewel worth at least 1,000 gp, which the spell consumes)
V, S, M (a pinch of diamond dust worth 25 gp sprinkled over the target, which the spell consumes)
V, S, M (a powder composed of diamond, emerald, ruby, and sapphire dust worth at least 5,000 gp, which the spell consumes)
V, S, M (a shard of onyx and a drop of the caster's blood, both of which the spell consumes)
V, S, M (a small bit of honeycomb and jade dust worth at least 10 gp, which the spell consumes)
V, S, M (a small piece of adamantine worth at least 500 gp, which the spell consumes)
V, S, M (a spool of platinum cord worth at least 250 gp, which the spell consumes)
V, S, M (a sprinkle of holy water and diamonds worth at least 25,000 gp, which the spell consumes)
V, S, M (a vial of quicksilver worth 500 gp and a life-sized human doll, both of which the spell consumes, and an intricate crystal rod worth at least 1,500 gp that is not consumed)
V, S, M (a white pearl worth at least 100 gp, which the spell consumes)
V, S, M (an agate worth at least 1,000 gp, which the spell consumes)
V, S, M (an hourglass filled with diamond dust worth at least 5,000 gp, which the spell consumes)
V, S, M (an ointment for the eyes that costs 25 gp; is made from mushroom powder, saffron, and fat; and is consumed by the spell)
V, S, M (clay, ash, and mandrake root, all of which the spell consumes, and a jewel-encrusted dagger worth at least 1,000 gp)
V, S, M (diamond dust worth 100 gp, which the spell consumes)
V, S, M (diamond dust worth at least 100 gp, which the spell consumes)
V, S, M (diamonds worth 300 gp, which the spell consumes)
V, S, M (for each creature you affect with this spell, you must provide one jacinth worth at least 1,000 gp and one ornately carved bar of silver worth at least 100 gp, all of which the spell consumes)
V, S, M (gold dust worth at least 25 gp, which the spell consumes)
V, S, M (herbs, oils, and incense worth at least 1,000 gp, which the spell consumes)
V, S, M (holy water or powdered silver and iron worth at least 100 gp, which the spell consumes)
V, S, M (holy water or powdered silver and iron, which the spell consumes)
V, S, M (incense and a sacrificial offering appropriate to your religion, together worth at least 25 gp, which the spell consumes)
V, S, M (incense and powdered diamond worth at least 200 gp, which the spell consumes)
V, S, M (incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each)
V, S, M (mercury, phosphorus, and powdered diamond and opal with a total value of at least 1,000 gp, which the spell consumes)
V, S, M (mistletoe, which the spell consumes, that was harvested with a golden sickle under the light of a full moon)
V, S, M (rare oils and unguents worth at least 1,000 gp, which the spell consumes)
V, S, M (ruby dust worth 50 gp, which the spell consumes)
V, S, M (snow or ice in quantities sufficient to made a life-size copy of the duplicated creature; some hair, fingernail clippings, or other piece of that creature's body placed inside the snow or ice; and powdered ruby worth 1,500 gp, sprinkled over the duplicate and consumed by the spell)

So actually: yes, there are.  Exceptions:

V, S, M (a vial of quicksilver worth 500 gp and a life-sized human doll, both of which the spell consumes, and an intricate crystal rod worth at least 1,500 gp that is not consumed)
V, S, M (clay, ash, and mandrake root, all of which the spell consumes, and a jewel-encrusted dagger worth at least 1,000 gp)
V, S, M (incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each)

Other exceptions:
V, S, M (for each creature you affect with this spell, you must provide one jacinth worth at least 1,000 gp and one ornately carved bar of silver worth at least 100 gp, all of which the spell consumes)

More exceptions (some of which are the same ones):
components with two sets of monetary value in them
>>> has_two = partial(re.search, r'[0-9][0-9, ]*.*[^0-9, ].*[0-9][0-9, ]*')
>>> jprint(filter(has_two, components))
V, S, M (a diamond worth at least 1,000 gp and at least 1 cubic inch of flesh of the creature that is to be cloned, which the spell consumes, and a vessel worth at least 2,000 gp that has a sealable lid and is large enough to hold a Medium creature, such as a huge urn, coffin, mud-filled cyst in the ground, or crystal container filled with salt water)
V, S, M (a vial of quicksilver worth 500 gp and a life-sized human doll, both of which the spell consumes, and an intricate crystal rod worth at least 1,500 gp that is not consumed)
V, S, M (an exquisite chest, 3 feet by 2 feet by 2 feet, constructed from rare materials worth at least 5,000 gp, and a Tiny replica made from the same materials worth at least 50 gp)
V, S, M (for each creature you affect with this spell, you must provide one jacinth worth at least 1,000 gp and one ornately carved bar of silver worth at least 100 gp, all of which the spell consumes)
V, S, M (incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each)

Are there any other monetary "each" instances?
>>> each = [c for c in havem if c.find('each') > -1]
>>> jprint(each)
V, S, M (a miniature portal carved from ivory, a small piece of polished marble, and a tiny silver spoon, each item worth at least 5 gp)
V, S, M (a pair of platinum rings worth at least 50 gp each, which you and the target must wear for the duration)
V, S, M (a pinch of salt and one copper piece placed on each of the corpse's eyes, which must remain there for the duration)
V, S, M (for each creature you affect with this spell, you must provide one jacinth worth at least 1,000 gp and one ornately carved bar of silver worth at least 100 gp, all of which the spell consumes)
V, S, M (incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each)
V, S, M (one clay pot filled with grave dirt, one clay pot filled with brackish water, and one 150 gp black onyx stone for each corpse)
V, S, M (seven sharp thorns or seven small twigs, each sharpened to a point)

------------------------
If updates change the output of the above 3 tests,
new exceptions may need to be added to datatypes.components_exceptions;
changes may also need to be made to parse.SpellParser.parse_material_value
"""
from dnd5edb import parse
re_components = parse.SpellParser.re_components
re_value = parse.SpellParser.re_value
from dnd5edb.db_analysis import subnode_tags, string_tags, tag_count
from pprint import pprint
from functools import partial
pprint = partial(pprint, width=1000)
jprint = lambda lines: print('\n'.join(lines))
import re
