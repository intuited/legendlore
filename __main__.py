import sys

if __name__ == '__main__':
    tree = parse_db()
    #spell_tag_analysis(tree)
    parsed = list(parse_spells(tree))
    parsed_spells_analysis(parsed)
