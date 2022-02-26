#!/usr/bin/env python3
"""Main file meant to serve as an entry point into analysis routines.

Creating and executing an appropriately named symlink to this file will run the
named analysis routine.

The analysis routines were created to facilitate exploration of the database
during `legendlore` development and are largely vestigial.

Valid options for symlinks:
    - analyze_fey
    - analyze_monster_nodes
    - knowledge_cleric_spells
"""
import sys
from legendlore import analysis

if __name__ == '__main__':
    command = sys.argv[1].split('/')[-1]
    getattr(analysis, command)()
