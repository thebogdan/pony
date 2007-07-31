# import os.path
# xslt_filename = os.path.join(os.path.dirname(__file__), 'transform.xslt')
# xslt = etree.XSLT(etree.parse(xslt_filename))

from lxml import etree
from lxml.etree import SubElement

from pony.utils import import_module

def normalize(html):
    # print etree.tostring(html, pretty_print=True), '\n'
    head = html.find('head')
    body = html.find('body')
    if body is None: body = SubElement(html, 'body')
    if head is None:
        head = html.makeelement('head')
        html.insert(-1, head)
    head_list = layout_tags_xpath(head)
    body[0:0] = head_list
    if head_list: pass
    elif layout_tags_xpath(body): pass
    else:
        for p in body.findall('p'):
            if layout_tags_xpath(p): break
        else: return
    i = 0
    while i < len(body):
        x = body[i]
        tag = x.tag
        if tag == 'p': unnest_p(x)
        elif tag in layout_tags:
            if tag == 'layout': unnest_layout(x)
            elif tag == 'row': unnest_row(x)
            else: unnest_element(x)
        i += 1
    # print etree.tostring(html, pretty_print=True), '\n'
    elements = []
    row = None
    text = body.text
    if text and not text.isspace():
        row = body.makeelement('row')
        row.text = text
        body.text = None
        elements.append(row)
    for x in body:
        tag = x.tag
        if tag in layout_tags and tag != 'column':
            if row is not None: normalize_row(row)
            row = None
            elements.append(x)
            tail = x.tail
            layout_tags[tag](x)
            if tail and not tail.isspace():
                row = body.makeelement('row')
                row.text = tail
                x.tail = None
                elements.append(row)
        else:
            if row is None:
                row = body.makeelement('row')
                elements.append(row)
            row.append(x)
    if row is not None: normalize_row(row)
    body[:] = elements
    # print etree.tostring(html, pretty_print=True), '\n'

def normalize_layout(layout):
    normalize_width(layout)

def normalize_header(header):
    pass

def normalize_footer(footer):
    pass

def normalize_sidebar(sidebar):
    normalize_width(sidebar)

def normalize_row(row):
    elements = []
    column = None
    text = row.text
    if text and not text.isspace():
        column = row.makeelement('column')
        column.text = text
        row.text = None
        elements.append(column)
    for x in row:
        if x.tag == 'column':
            if column is not None: normalize_column(column)
            column = None
            elements.append(x)
            tail = x.tail
            normalize_column(x)
            if tail and not tail.isspace():
                column = row.makeelement('column')
                column.text = tail
                x.tail = None
                elements.append(column)
        else:
            if column is None:
                column = row.makeelement('column')
                elements.append(column)
            column.append(x)
    if column is not None: normalize_column(column)
    row[:] = elements
    width_list = correct_width_list([column.get('width') for column in row])
    for column, width in zip(row, width_list):
        column.set('width', width or '')
    row.set('pattern', '-'.join(width or '?' for width in width_list))

yui_columns = {
    2 : [ ('1/2', '1/2'),
          ('1/3', '2/3'), ('2/3', '1/3'),
          ('1/4', '3/4'), ('3/4', '1/4') ],
    3 : [ ('1/3', '1/3', '1/3'),
          ('1/2', '1/4', '1/4'),
          ('1/4', '1/4', '1/2') ],
    4 : [ ('1/4', '1/4', '1/4', '1/4') ]
    }

def correct_width_list(width_list):
    for i, width in enumerate(width_list):
        if width == '2/4': width_list[i] = '1/2'
    lists = yui_columns.get(len(width_list))
    if lists is None: return width_list
    for list in lists:
        for w1, w2 in zip(width_list, list):
            if w1 and w1 != w2: break
        else: return list
    return width_list

def normalize_column(column):
    elements = []
    p = None
    text = column.text
    if text and not text.isspace():
        p = column.makeelement('p')
        p.text = text
        column.text = None
        elements.append(p)
    for x in column:
        if x.tag in block_level_tags:
            p = None
            elements.append(x)
            tail = x.tail
            if tail and not tail.isspace():
                p = column.makeelement('p')
                p.text = tail
                x.tail = None
                elements.append(p)
        else:
            if p is None:
                p = column.makeelement('p')
                elements.append(p)
            p.append(x)
    column[:] = elements

def normalize_width(element):
    width = element.get('width')
    if width is None or width[-2:] != 'px': return
    try: number = int(width[:-2])
    except ValueError: return
    element.set('width', width[:-2])

layout_tags = dict(
    layout=normalize_layout,
    header=normalize_header,
    footer=normalize_footer,
    sidebar=normalize_sidebar,
    row=normalize_row,
    column=normalize_column,
    )
layout_tags_xpath = etree.XPath('|'.join(layout_tags))

block_level_tags = set('''
    address blockquote center dir div dl fieldset form h1 h2 h3 h4 h5 h6 hr
    isindex menu noframes noscript ol p pre table ul'''.split())

def _unnest(x):
    parent = x.getparent()
    tail = parent.tail
    if tail and not tail.isspace():
        last = parent[-1]
        last.tail = (last.tail or '') + tail
        parent.tail = None
    parent2 = parent.getparent()
    i = parent.index(x)
    j = parent2.index(parent)
    parent2[j+1:j+1] = parent[i:]

def unnest_p(p):
    i = 0
    while i < len(p):
        x = p[i]
        if x.tag in layout_tags: _unnest(x)
        i += 1

def unnest_layout(layout):
    if len(layout): _unnest(layout[0])
    text = layout.text
    if text and not text.isspace():
        layout.text = None
        layout.tail = text

def unnest_row(row):
    i = 0
    while i < len(row):
        x = row[i]
        tag = x.tag
        if tag == 'p': unnest_p(x)
        elif tag == 'column': unnest_element(x)
        elif tag in layout_tags: _unnest(x)
        i += 1

def unnest_element(element):
    i = 0
    while i < len(element):
        x = element[i]
        tag = x.tag
        if tag == 'p': unnest_p(x)
        elif tag in layout_tags: _unnest(x)
        i += 1

def move_content(target, source_list):
    for source in source_list:
        text = source.text
        if text and not text.isspace():
            if len(target):
                last = target[-1]
                last.tail = (last.tail or '') + text
            else: target.text = (target.text or '') + text
        target.extend(source[:])

class LayoutError(Exception): pass

def transform(html):
    body = html.find('body')
    layout = body.find('layout')
    layout_type = 'yui'
    if layout is not None: layout_type = layout.get('type', layout_type)
    try: module = import_module('pony.layout.' + layout_type)
    except ImportError:
        raise LayoutError('Invalid layout type: %s' % layout_type)
    return module.transform(html)
