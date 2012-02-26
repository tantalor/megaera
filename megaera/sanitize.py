from google.appengine.api import datastore_types


def sanitize(obj, urlize):
  """Sanitize for json or yaml output."""
  if isinstance(obj, dict):
    # a dictionary
    return dict([(key, sanitize(value, urlize)) for key, value in obj.iteritems()])
  if hasattr(obj, '__iter__'):
    # a iterable sequence
    return [sanitize(v, urlize) for v in obj]
  if hasattr(obj, 'sanitize'):
    # a sanitizeable object
    return obj.sanitize(urlize)
  # default: stringify
  return str(obj)
