import re

from google.appengine.api import urlfetch


__charset_rx__ = re.compile('charset=(\S*)', re.IGNORECASE)


def response_charset(response):
  """Get the charset of a response."""
  content_type = response.headers.get('content-type')
  if content_type:
    match = __charset_rx__.search(content_type)
    if match:
      return match.group(1)

def decode_response(response, default_charset='utf-8'):
  """Decode a response into unicode, fallback to ASCII."""
  charset = response_charset(response) or default_charset
  try:
    return unicode(response.content, charset)
  except UnicodeDecodeError:
    return response.content

def fetch_decode(url, **kwargs):
  """Decode the content of a URL."""
  response = fetch(url)
  if response:
    return decode_response(response, **kwargs)

def fetch(url):
  return urlfetch.fetch(url.replace(' ', '%20'))
