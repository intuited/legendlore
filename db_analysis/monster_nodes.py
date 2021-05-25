"""monster_nodes.py

Analysis routines, largely independent of the dnd5edb module, which provide information about the database.

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
"""
from dnd5edb import parse
from dnd5edb.db_analysis import subnode_tags, string_tags, tag_count

from functools import reduce
from collections import Counter
