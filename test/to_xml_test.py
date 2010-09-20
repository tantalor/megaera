# -*- coding: utf-8 -*-


import unittest

from megaera import to_xml


class TestToXML(unittest.TestCase):
  def test_string(self):
    self.assertEquals(
      to_xml('foo'),
u"""<?xml version="1.0" ?>
<data>
  foo
</data>
""".encode('utf8'),
    )
  def test_object(self):
    self.assertEquals(
      to_xml(dict(foo='bar')),
u"""<?xml version="1.0" ?>
<data>
  <foo>
    bar
  </foo>
</data>
""".encode('utf8'),
    )
  def test_nested_object(self):
    self.assertEquals(
      to_xml(dict(foo=dict(bar='baz'))),
u"""<?xml version="1.0" ?>
<data>
  <foo>
    <bar>
      baz
    </bar>
  </foo>
</data>
""".encode('utf8'),
    )
  def test_sequence(self):
    self.assertEquals(
      to_xml(['a', 'b', 'c']),
u"""<?xml version="1.0" ?>
<data>
  <value>
    a
  </value>
  <value>
    b
  </value>
  <value>
    c
  </value>
</data>
""".encode('utf8'),
    )
  def test_nested_sequence(self):
    self.assertEquals(
      to_xml([['a', 'b'], ['c', 'd']]),
u"""<?xml version="1.0" ?>
<data>
  <value>
    <value>
      a
    </value>
    <value>
      b
    </value>
  </value>
  <value>
    <value>
      c
    </value>
    <value>
      d
    </value>
  </value>
</data>
""".encode('utf8'),
    )
  def test_unicode(self):
    self.assertEquals(
      to_xml(dict(foo=u'bar’baz')),
u"""<?xml version="1.0" ?>
<data>
  <foo>
    bar’baz
  </foo>
</data>
""".encode('utf8'),
    )
  def test_object_sequence(self):
    self.assertEquals(
      to_xml(dict(foo=['bar', 'baz'])),
u"""<?xml version="1.0" ?>
<data>
  <foo>
    bar
  </foo>
  <foo>
    baz
  </foo>
</data>
""".encode('utf8'),
    )

if __name__ == '__main__':
  unittest.main()
