"""Functions and objects used by doctests in the module code."""
import dnd5edb

s = dnd5edb.Spells()

def aobj(value, attr='a'):
    """Generate a simple object with attribute `attr` set to `value`."""
    class TestClass():
        None
    o = TestClass()
    setattr(o, attr, value)
    return o
