"""monster_nodes.py

Analysis routines, largely independent of the dnd5edb module, which provide information about the database.

Pull the tree data, select monsters from the tree
>>> tree = parse.XML.get_tree()
>>> monsters = tree.xpath('//monster')

print(monsters[0])
print(dir(monsters[0]))
print(list(monsters[0].iterchildren()))
print(dir(list(monsters[0].iterchildren())[0]))

print(tags_in_monster_node(monsters[0]))

Get the set of unique tags of child nodes of monster nodes
>>> all_tags = reduce(set.union, (tags_in_monster_node(m) for m in monsters), set())

There are some tags that are not strings and instead repr as, e.g., "<cyfunction Comment at 0x7f660c4d7a00>"
>>> string_tags = (tag for tag in all_tags if type(tag) is str)

>>> sorted(string_tags)
['ac', 'action', 'alignment', 'cha', 'con', 'conditionImmune', 'cr', 'description', 'dex', 'environment', 'hp', 'immune', 'int', 'languages', 'legendary', 'name', 'passive', 'reaction', 'resist', 'save', 'senses', 'size', 'skill', 'slots', 'speed', 'spells', 'str', 'trait', 'type', 'vulnerable', 'wis']
"""
from dnd5edb import parse
from functools import reduce

def tags_in_monster_node(node):
    """Returns set of tags of child nodes of `node`."""
    children = node.iterchildren()
    return set(child.tag for child in children)
