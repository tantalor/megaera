from google.appengine.api.datastore_errors import NeedIndexError

def get(handler, response):
  name = handler.request.get('name')
  if name == 'notfound':
    return handler.not_found()
  if name == 'needindex':
    raise NeedIndexError()
  if name == 'error':
    raise Exception('generic error')
  response.messages.hello = "hello %s" % name
