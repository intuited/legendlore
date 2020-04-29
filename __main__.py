import sys
from dnd5edb import analysis

if __name__ == '__main__':
    print(f"__main__:  sys.argv: {sys.argv}")
    command = sys.argv[0].split('/')[-1]
    switch = {'analyze_monster_nodes': analysis.analyze_monster_nodes}
    switch[command]()
    #tree = parse_db()
    ##spell_tag_analysis(tree)
    #parsed = list(parse_spells(tree))
    #parsed_spells_analysis(parsed)
