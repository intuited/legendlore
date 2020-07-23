#!/usr/bin/env python3
import sys
from dnd5edb import analysis

if __name__ == '__main__':
    command = sys.argv[0].split('/')[-1]
    getattr(analysis, command)()
