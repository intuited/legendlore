"""Rip the spell database from dnd-spells.com and save it as JSON."""
from requests import get
from lxml import etree
from io import StringIO

parser = etree.HTMLParser()

def load_tree(url):
    page = get(url)
    return etree.parse(StringIO(page.text), parser)

def spell_page_urls(spell_list_url='https://www.dnd-spells.com/spells'):
    tree = load_tree(spell_list_url)
    urls = tree.xpath('//table/tbody/tr/td/a[1]/@href')
    return urls

def parse_spell_page(spell_url):
    tree = load_tree(spell_url)
    content = tree.xpath('//div[@class="col-md-12"]')[0]
    title = content.xpath('h1[@class="classic-title"]/span[1]')[0].text
    source = content.xpath('span')
    if source:
        source = source[0].text
    else:
        source = None
    school = content.xpath('p')[0].text
    attribs = content.xpath('p')[1]
    print('etree.tostring(attribs): {0}'.format(etree.tostring(attribs)))
    print('attribs: {0}'.format(attribs))
    print('attribs.text: {0}'.format(attribs.text))
    print('attribs.keys(): {0}'.format(attribs.keys()))
    print('attribs.items(): {0}'.format(attribs.items()))
    print('attribs.getchildren(): {0}'.format(attribs.getchildren()))
    print('attribs.getchildren().text: {0}'.format([a.text for a in attribs.getchildren()]))
    """
    etree.tostring(attribs): b'<p>&#13;\n                Level: <strong>Cantrip</strong> <br/>&#13;\n                Casting time: <strong>1 Action</strong> <br/>&#13;\n                Range: <strong>60 feet</strong> <br/>&#13;\n                Components: <strong>V, S</strong> <br/>&#13;\n                Duration: <strong>Instantaneous</strong> <br/>&#13;\n                </p>'
    attribs: <Element p at 0x1062b3a00>
    attribs.text:
                    Level:
    attribs.keys(): []
    attribs.items(): []
    attribs.getchildren(): [<Element strong at 0x106c02eb0>, <Element br at 0x106c37dc0>, <Element strong at 0x106c37cd0>, <Element br at 0x106c37f00>, <Element strong at 0x106c37d20>, <Element br at 0x105b7a7d0>, <Element strong at 0x1062cafa0>, <Element br at 0x106394af0>, <Element strong at 0x1063a3f00>, <Element br at 0x1063a39b0>]
    attribs.getchildren().text: ['Cantrip', None, '1 Action', None, '60 feet', None, 'V, S', None, 'Instantaneous', None]
    """
    exit()
    # print(dir(attribs))
    # ['__bool__', '__class__', '__contains__', '__copy__', '__deepcopy__', '__delattr__', '__delitem__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__len__', '__lt__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__', '_init', 'addnext', 'addprevious', 'append', 'attrib', 'base', 'clear', 'cssselect', 'extend', 'find', 'findall', 'findtext', 'get', 'getchildren', 'getiterator', 'getnext', 'getparent', 'getprevious', 'getroottree', 'index', 'insert', 'items', 'iter', 'iterancestors', 'iterchildren', 'iterdescendants', 'iterfind', 'itersiblings', 'itertext', 'keys', 'makeelement', 'nsmap', 'prefix', 'remove', 'replace', 'set', 'sourceline', 'tag', 'tail', 'text', 'values', 'xpath']

    return {'url':      spell_url,
            'title':    title,
            'source':   source,
            'school':   school,
            'attribs':  attribs,
            }

for url in spell_page_urls():
    print(parse_spell_page(url))
