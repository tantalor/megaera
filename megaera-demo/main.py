from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp.util import run_wsgi_app

from megaera import RequestHandler, get_jinja2_env

# install a jinja2 filter
jinja2_env = get_jinja2_env()
jinja2_env.filters['bold'] = lambda s: "<b>%s</b>" % s

application = WSGIApplication([
  RequestHandler.path_with_page('/', 'handlers.default'),
], debug=True)
