"""db_analysis

Inquiries into the nature of the database, used to write parsing code.
"""
from functools import reduce
from collections import defaultdict

def tags_in_node(node):
    """Returns set of tags of child nodes of `node`."""
    children = node.iterchildren()
    return set(child.tag for child in children)

# Returns the set of unique tags of child nodes of all nodes in `col`
subnode_tags = lambda col: reduce(set.union, (tags_in_node(n) for n in col), set())

# There are some tags that are not strings and instead repr as, e.g., "<cyfunction Comment at 0x7f660c4d7a00>"
string_tags = lambda tags: sorted(tag for tag in tags if type(tag) is str)

# Number of nodes in `nodes` which have a subnode with tag `tagname`
tag_count = lambda nodes, tagname: len([c for n in nodes for c in n if c.tag == tagname])

def get_name(node):
    """Returns the text of the child field with tag "name"."""
    for child in node.iterchildren():
        if child.tag == 'name':
            return child.text

def groupeddict(it):
    d = defaultdict(list)
    for k, v in it:
        d[k].append(v)
    return d
histogram = lambda d: {k: len(v) for k, v in d.items()}
