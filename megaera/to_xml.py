from xml.dom.minidom import Document


def to_xml(value, root='data', indent='  '):
  """Returns XML from dicts or seqs."""
  doc = Document()
  if hasattr(value, '__iter__') and not isinstance(value, dict):
    # special case for top-level sequence
    parent = doc.createElement(root)
    doc.appendChild(parent)
    add(doc, parent, 'value', value)
  else:
    add(doc, doc, root, value)
  return doc.toprettyxml(indent=indent)

def add(doc, parent, key, value):
  """Adds value to document under parent as key."""
  if isinstance(value, dict):
    child = doc.createElement(key)
    parent.appendChild(child)
    for item in value.iteritems():
      add(doc, child, *item)
  elif hasattr(value, '__iter__'):
    for item in value:
      if hasattr(item, '__iter__') and not isinstance(item, dict):
        child = doc.createElement('value')
        parent.appendChild(child)
        add(doc, child, 'value', item)
      else:
        add(doc, parent, key, item)
  else:
    # default: text node
    if isinstance(value, unicode):
      text = value.encode('utf8')
    else:
      text = str(value)
    child = doc.createElement(key)
    child.appendChild(doc.createTextNode(text))
    parent.appendChild(child)
