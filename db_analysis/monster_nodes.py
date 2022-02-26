"""monster_nodes.py

Analysis routines, largely independent of the legendlore module, which provide information about the database.

This functionality is already present in analysis.py but this version is a bit more readable?
Mostly I just forgot about that whole function and wrote this instead.

Pull the tree data, select monsters from the tree
>>> tree = parse.XML.get_tree()
>>> monsters = tree.xpath('//monster')

Get the set of unique tags of child nodes of monster nodes
>>> monster_tags = subnode_tags(monsters)

All tags of child nodes of <monster> nodes
>>> string_tags(monster_tags)
['ac', 'action', 'alignment', 'cha', 'con', 'conditionImmune', 'cr', 'description', 'dex', 'environment', 'hp', 'immune', 'int', 'languages', 'legendary', 'name', 'passive', 'reaction', 'resist', 'save', 'senses', 'size', 'skill', 'slots', 'speed', 'spells', 'str', 'trait', 'type', 'vulnerable', 'wis']

>>> actions = [child for monster in monsters for child in monster if child.tag == 'action']
>>> action_tags = string_tags(subnode_tags(actions))

Actions are comprised of subnodes with these three tags
>>> action_tags
['attack', 'name', 'text']

All Actions have a name node; some have attack nodes; all/some have one or more text nodes.
>>> [f'{tag} x{tag_count(actions, tag)}' for tag in action_tags]
['attack x3701', 'name x5594', 'text x6409']

Turns out all Actions have at least one text node.
>>> len([n for n in actions if len([c for c in n if c.tag == 'text']) == 0])
0

Maximum child nodes per action: apparently a lot!
>>> reduce(max, (len(list(n.iterchildren())) for n in actions))
26

What has 26 child nodes??
>>> [f'{n.find("name").text}' for n in actions if len(list(n.iterchildren())) == 26]
['Variant: Flesh Warping']

Uh, ..sure.  Seems legit.

So one last thing to confirm for actions: are there any subnodes of subnodes of actions?
>>> action_subnodes = list(c for n in actions for c in n.iterchildren())
>>> len(action_subnodes)
15704
>>> action_subnode_subnodes = list(c for n in action_subnodes for c in n.iterchildren())
>>> len(action_subnode_subnodes)
0

Okay, so that was pretty much as expected, especially since 2220 + 3399 + 7472 == 13091

What do Attack fields look like?
>>> attacks = tree.xpath('//monster/action/attack')
>>> [n.text for n in attacks][:20]
['Slam|+8|2d12+4', 'Slam|+6|2d10+2', 'Slam|+5|2d6+1', 'Slam|+6|1d8+2', 'Slam|+8|1d4+4', 'Bite|+1|1d4-1', 'Talon|+4|1d4+2', 'Javelin|+4|1d6+2', 'Tentacle|+9|2d6+5', 'Tentacle||1d12', 'Tail|+9|3d6+5', 'Claw|+11|2d6+7', 'Chilling Gaze||6d6', 'Cold Breath (Recharge 6)||10d8', 'Club|+2|1d4', 'Bite|+11|2d10+6', 'Claw|+11|2d6+6', 'Tail|+11|2d8+6', 'Acid Breath (Recharge 5-6)||12d8', 'Bite|+13|2d10+7']

Does the first of those three fields always match the text of the action `name` element?
>>> actions = tree.xpath('//monster/action')
>>> nomatch = [n for n in actions if 'attack' in tags_in_node(n) and get_name(n) != get_attack_name(n)]
>>> len(nomatch)
1

The sole exception has no name element.  Appears to be an action element for a vehicle called a "battle balloon".
>>> pprint([(c.tag, c.text) for c in nomatch[0].iterchildren()])
[('text',
  'On its turn the battle balloon can take 3 actions if it has twenty or more crew, 2 actions if it has ten or more '
  'crew, or 1 action if it has fewer than ten crew, choosing from the options below. It cannot take any actions if it '
  'has no remaining crew.'),
 ('text', '• Fire Ballista. The battle balloon can fire its harpoon guns.'),
 ('text', '• Fire Green Flame Arbalester. The battle balloon can fire its green flame arbalester.'),
 ('text',
  '• Move. The battle balloon can use its helm to move using its propeller. If the battle balloon enters a Large or '
  "smaller creature's space, that creature is automatically pushed to the edge of the battle balloon's space. The "
  'creature must also succeed on a DC 15 Dexterity saving throw or take 5 (1d10) bludgeoning damage.'),
 ('attack', '||1d10'),
 ('text',
  '• Harpoon Haul. The battle balloon can pull each target grappled by it up to 30 feet toward the battle balloon.')]


## Analysis of parsed data structures
# These explorations use the processed XML data.

Alignment values:
>>> pprint(Counter(getattr(n, 'alignment', None) for n in m))
Counter({'Unaligned': 462,
         'Chaotic Evil': 328,
         'Lawful Evil': 305,
         'Neutral Evil': 271,
         'Any alignment': 267,
         'Neutral': 140,
         'Lawful Good': 66,
         'Chaotic Neutral': 65,
         'Chaotic Good': 62,
         'Lawful Neutral': 55,
         'Neutral Good': 30,
         'Any Non-Good Alignment': 27,
         'Any Non-Lawful Alignment': 12,
         'Any Evil Alignment': 11,
         'Any Chaotic Alignment': 9,
         'Neutral Good (50%) Neutral Evil (50%)': 8,
         'Chaotic Good (75%) Neutral Evil (25%)': 1,
         "as the eidolon's alignment": 1,
         'Neutral Good Neutral Evil': 1})
"""
from legendlore import parse
from legendlore.db_analysis import tags_in_node, subnode_tags, string_tags, tag_count, get_name, groupeddict, histogram
from repltools import m

from functools import reduce, partial
from pprint import pprint
pprint = partial(pprint, width=120)
from collections import Counter

def get_attack_name(node):
    """Returns the first of the three '|'-delimited fields in the 'text' field of the child 'attack' node."""
    for child in node.iterchildren():
        if child.tag == 'attack':
            return child.text.split('|')[0]
