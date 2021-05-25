"""spell_nodes.py

Similar to monster_nodes: provides analysis of <spell> nodes in the xml database.

Pull the tree data, select spells from the tree
>>> tree = parse.XML.get_tree()
>>> spells = tree.xpath('//spell')

All string tags of spell nodes
>>> string_tags(subnode_tags(spells))
['classes', 'components', 'duration', 'level', 'name', 'range', 'ritual', 'roll', 'school', 'text', 'time']
"""
from dnd5edb import parse
from dnd5edb.db_analysis import subnode_tags, string_tags, tag_count
