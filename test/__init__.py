"""Functions and objects used by doctests in the module code."""
import dnd5edb

s = dnd5edb.Spells()

class BlankClass():
    None

def aobj(value, attr='a'):
    """Generate a simple object with attribute `attr` set to `value`."""
    o = BlankClass()
    setattr(o, attr, value)
    return o

def obj_fromdict(d):
    o = BlankClass()
    for k, v in d.items():
        setattr(o, k, v)
    return o

fakenode = lambda tag, v: obj_fromdict({'tag': tag, 'text': v})
