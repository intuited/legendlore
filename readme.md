## dnd5edb ##

Python API to run queries on and format data from XML data for D&D 5th ed.

The XML data is built for an Android app called Fight Club and is not licensed content.
As such, it may be somewhat difficult to locate.  Most recently, it appears to live in [this DropBox][0]

The purpose of this code is to enable convenient programmatic access to the database.

For example:

    >>> from dnd5edb import Spells, Monsters

    >>> Spells().where(level=4, classes=p.in_('Bard'))
    [Spell(Compulsion A/30'/C<=1m (4:B)),
     Spell(Confusion A/90'/C<=1m (4:B+D+AT+S+Wz)),
     Spell(Dimension Door A/500'/I (4:B+S+Wl+Wz)),
     Spell(Freedom of Movement A/T/1h (4:A+B+C+D+Ra)),
     Spell(Greater Invisibility A/T/C<=1m (4:B+B+RGS+AT+S+WlA+Wz)),
     Spell(Hallucinatory Terrain 10m/300'/24h (4:B+D+AT+Wl+Wz)),
     Spell(Locate Creature A/S/C<=1h (4:B+C+D+P+Ra+WlR+WlS+Wz)),
     Spell(Polymorph A/60'/C<=1h (4:B+D+S+Wz)),
     Spell(Charm Monster A/30'/1h (4:B+D+AT+S+Wl+Wz))]

    >>> print(Spells().where(name=p.in_('Circle')).fmt())
    Circle of Death A/150'/I (6:S+Wl+Wz)
    Circle of Power A/S(30'r)/C<=10m (5:P)
    Circle of Power* A/S(30'r)/C<=10m (5:PCr)
    Magic Circle 1m/10'/1h (3:C+FEK+P+RMS+Wl+Wz)
    Magic Circle* 1m/10'/1h (3:CA)
    Teleportation Circle 1m/10'/1r (5:B+RHW+S+Wz)
    Teleportation Circle* 1m/10'/1r (5:CA)

    >>> print(Spells().search('Magic Missile')[0].fmt_pointform())
    - Magic Missile A/120'/I (1:FEK+S+Wz)
      - You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.
      - 
      - At Higher Levels: When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot above 1st.

    >>> Monsters().search('AAR')[0]
    Monster({'name': Aarakocra, 'type': humanoid (aarakocra)})

    The basic functionality is accessed by the Spells and Monsters classes.
    There are other node types in the database, but for now these are the only ones being processed.

### Installation ###

Once you manage to find a copy of the XML database, put it in a subdirectory of the dnd5edb code called `FC5eXML`.
Currently the code looks for the file CoreOnly.xml in that directory.  That file is located in the "Collections" directory of [the DropBox][0].

[0]: https://www.dropbox.com/sh/v4qy66rxi8gpexs/AAADWx5AC55J_A9Ni0rWzWB8a?dl=0&fbclid=IwAR0Vx1n6MmVGuL05jsVsIAvSgUDti1vF5onwA75QGZ3JdWcSk8MgVi4Y12c

