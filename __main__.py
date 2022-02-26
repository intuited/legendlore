#!/usr/bin/env python3
import sys
from legendlore import analysis

if __name__ == '__main__':
    command = sys.argv[1].split('/')[-1]
    getattr(analysis, command)()
