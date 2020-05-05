#!/usr/bin/env python3
import sys
from dnd5edb import analysis

if __name__ == '__main__':
    command = sys.argv[0].split('/')[-1]
    switch = {'analyze_monster_nodes': analysis.analyze_monster_nodes,
              'analyze_fey': analysis.analyze_fey,
    }
    switch[command]()
