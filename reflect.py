"""reflect: functions to report on contents of DB."""
def collection_attribs(col):
    """Returns a list of the unique non-subscripted attributes of items in `col`."""
    attribs = (attrib for item in col for attrib in item.__dict__ if attrib[0] != '_')
    return list(set(attribs))
