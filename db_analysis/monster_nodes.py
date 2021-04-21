"""monster_nodes.py

Analysis routines, largely independent of the dnd5edb module, which provide information about the database.
"""
from dnd5edb import parse
from functools import reduce

def subnodes_of_monster_nodes():
    """Finds all types of subnodes of <monster> nodes."""
    tree = parse.XML.get_tree()
    monsters = tree.xpath('//monster')

    print(monsters[0])
    print(dir(monsters[0]))
    print(list(monsters[0].iterchildren()))
    print(dir(list(monsters[0].iterchildren())[0]))

    def tags_in_monster_node(node):
        """Returns set of tags of child nodes of `node`."""
        children = node.iterchildren()
        return set(child.tag for child in children)

    print(tags_in_monster_node(monsters[0]))

    all_tags = reduce(set.union, (tags_in_monster_node(m) for m in monsters), set())

    # There are some tags that are not strings and instead repr as "<cyfunction Comment at 0x7f660c4d7a00>"
    print(sorted(tag for tag in all_tags if type(tag) is str))
    # ['ac', 'action', 'alignment', 'cha', 'con', 'conditionImmune', 'cr', 'description', 'dex', 'environment', 'hp', 'immune', 'int', 'languages', 'legendary', 'name', 'passive', 'reaction', 'resist', 'save', 'senses', 'size', 'skill', 'slots', 'speed', 'spells', 'str', 'trait', 'type', 'vulnerable', 'wis']

subnodes_of_monster_nodes()
