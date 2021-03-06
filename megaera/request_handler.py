import logging
import os
import re
import sys
import traceback
import yaml
import types

from sanitize import sanitize
from recursivedefaultdict import recursivedefaultdict
import env
import json
import local
from to_xml import to_xml

from google.appengine.api import users, memcache
from google.appengine.api.datastore_errors import NeedIndexError
import webapp2
import jinja2

class NotFoundException(Exception):
  pass

HANDLERS_BASE  = 'handlers'
TEMPLATES_BASE = 'templates'
NOT_FOUND_HTML = 'not_found.html'
ERROR_HTML     = 'error.html'

MIME_JSON = 'application/json'
MIME_XML  = 'application/xml'
MIME_ATOM = 'application/atom+xml'

__JINJA2_ENV__ = None

def set_jinja2_env(jinja2):
  global __JINJA2_ENV__
  __JINJA2_ENV__ = jinja2
  return get_jinja2_env()

def get_jinja2_env():
  global __JINJA2_ENV__
  if not __JINJA2_ENV__:
    __JINJA2_ENV__ = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_BASE))
  return __JINJA2_ENV__

class RequestHandler(webapp2.RequestHandler):
  
  @classmethod
  def with_page(cls, page):
    if isinstance(page, types.ModuleType):
      return type(page.__file__, (cls,), dict(page=page))
    if isinstance(page, str):
      try:
        __import__(page)
        return cls.with_page(page=sys.modules[page])
      except ImportError:
        logging.error("missing handler for %s", page)
  
  @classmethod
  def path_with_page(cls, path, page):
    return (path+"\.?(yaml|json|xml|atom)?$", cls.with_page(page))
  
  def response_dict(self, **kwargs):
    """Returns the response dictionary and sets the given values."""
    if not hasattr(self, '__response_dict__'):
      setattr(self, '__response_dict__', recursivedefaultdict())
    if kwargs:
      self.__response_dict__.update(**kwargs)
    return self.__response_dict__
  
  def url_args(self):
    """Returns the URL arguments in the WSGI paths."""
    return self.__url_args__
  
  def url_arg(self, index):
    """Returns the URL arg at the given index or None."""
    return self.url_args()[index]
  
  def get(self, *args):
    """Responds to GET requests from WSGIApplication."""
    if self.has_param('post'):
      return self.post(*args)
    # check for trailing slashes
    match = re.compile('^(/.*[^/])/+$').search(self.request.path)
    if match and match.groups(1):
      # strip trailing slashes and redirect
      return self.redirect(match.group(1))
    # check if we can respond
    if hasattr(self.page, 'get'):
      # run the handler and get the template path
      path = self.handle(self.page.get, *args)
    else:
      # return with 405
      path = self.not_found(status=405)
    # render the template
    if self.is_atom():
      # for atom
      self.render(path, 'atom')
    else:
      # for html
      self.render(path)
  
  def post(self, *args):
    """Responds to POST requests from WSGIApplication"""
    self.__url_args__ = args
    # check if we can post
    if hasattr(self.page, 'post'):
      # run the handler and get the template path
      path = self.handle(self.page.post, *args)
    else:
      # return with 405
      path = self.not_found(status=405)
    # if we encountered errors, run the get handler
    if self.has_errors():
      self.get(*args)
    elif hasattr(self, '_is_redirect') and 'Location' in self.response.headers:
      location = self.response.headers['Location'];
      self.response.out.write("""Moved to <a href="%s">%s</a>\n""" % (location, location))
    else:
      # otherwise render the template
      self.render(path)
  
  def has_errors(self):
    """Returns if the response dictionary contains form errors."""
    return 'errors' in self.response_dict()
  
  def is_admin(self):
    """Returns if the current user is an admin."""
    return users.is_current_user_admin()
  
  def has_param(self, param):
    return len(self.request.get_all(param)) > 0
  
  def accepts(self, mime_type):
    """Returns true if this requests accepts the given MIME type"""
    accept = self.request.headers.get('Accept')
    if accept:
      return accept == mime_type
  
  def is_json(self):
    """Returns if the current request is for JSON."""
    return self.has_param('json') or self.request.path.endswith('.json') or self.accepts(MIME_JSON)
  
  def is_yaml(self):
    """Returns if the current request is for YAML."""
    return self.has_param('yaml') or self.request.path.endswith('.yaml')
  
  def is_xml(self):
    """Returns if the current request is for XML."""
    return self.has_param('xml') or self.request.path.endswith('.xml') or self.accepts(MIME_XML)
  
  def is_atom(self):
    """Returns if the current request is for Atom."""
    return self.has_param('atom') or self.request.path.endswith('.atom') or self.accepts(MIME_ATOM)
  
  def is_html(self):
    """Returns if the current request is for HTML."""
    return not self.is_json() and not self.is_yaml() and not self.is_xml() and not self.is_atom()
  
  def logout_url(self):
    """Returns the logout URL of the current request."""
    return users.create_logout_url(self.request.uri)
  
  def login_url(self):
    """Returns the login URL of the current request."""
    return users.create_login_url(self.request.uri)
  
  def host(self):
    """Returns the current host's name."""
    return self.environ('HTTP_HOST')
  
  def cache_key(self, page=None, vary=None):
    page_name = self.page_name(page=page)
    return '-'.join([str(x) for x in (page_name, vary) if x])
  
  def cached(self, vary=None):
    """Returns if the current page is cached and updates the response dict with the cached values."""
    if self.has_param('no_cache'):
      return
    cached = memcache.get(
      key=self.cache_key(vary=vary),
      namespace="handler-cache")
    if cached:
      # update the response
      self.response_dict(**cached)
      return True
  
  def cache(self, time=0, vary=None, **kwargs):
    """Caches and updates the response dict with the given values for the current page."""
    memcache.set(
      key=self.cache_key(vary=vary),
      value=kwargs,
      time=time,
      namespace="handler-cache")
    # update the response
    self.response_dict(**kwargs)
  
  def invalidate(self, page=None, vary=None):
    """Invalidates the cache for given page or the current page."""
    memcache.delete(
      key=self.cache_key(vary=vary, page=page),
      namespace="handler-cache")
  
  def page_name(self, page=None):
    """Returns the name of the given page or the current page."""
    if not page:
      page = self.page
    match = re.compile("%s/([^.]*)" % HANDLERS_BASE).search(page.__file__)
    if match:
      return match.group(1)
  
  def default_template(self, ext="html"):
    """Returns the path for the current page's default template."""
    name = self.page_name()
    if name:
      return "%s.%s" % (name, ext)
    raise Exception("failed to build default template for %s" % page)
  
  def handle(self, method, *args):
    """Invokes the given method and return the template path to render."""
    self.__url_args__ = args
    try:
      return method(self, self.response_dict())
    except NotFoundException:
      return self.not_found()
    except NeedIndexError:
      return self.not_found(status=503)
    except:
      return self.handle_error()
  
  def handle_error(self):
    """Prepares a traceback for 500 errors, returns error template path."""
    (error_type, error, tb) = sys.exc_info()
    tb_formatted = traceback.format_tb(tb)
    error_type = error_type.mro()[0].__name__
    self.response_dict(
      error=error,
      error_type=error_type,
      tb_formatted=tb_formatted)
    logging.error("%s: %s", error_type, error)
    self.set_status(status=500)
    return ERROR_HTML
  
  def urlize(self, path):
    url = 'http://' + self.host() + path
    if self.extension():
      url += self.extension()
    return url
  
  def render(self, path, base="html"):
    """Renders the given template or the default template, or JSON(P)/YAML."""
    if self.is_json():
      sanitized = sanitize(self.response_dict(), self.urlize)
      json_str = json.write(sanitized)
      callback = self.request.get('callback')
      if re.match("^[_a-z]([_a-z0-9])*$", callback, re.IGNORECASE):
        json_str = "%s(%s)" % (callback, json_str) # jsonp
      self.response.headers['Content-Type'] = "%s; charset=UTF-8" % MIME_JSON
      self.response.out.write(json_str)
      return
    if self.is_yaml():
      sanitized = sanitize(self.response_dict(), self.urlize)
      yaml_str = yaml.safe_dump(sanitized, default_flow_style=False)
      self.response.headers['Content-Type'] = "text/plain; charset=UTF-8"
      self.response.out.write(yaml_str)
      return
    if self.is_xml():
      sanitized = sanitize(self.response_dict(), self.urlize)
      xml_str = to_xml(value=sanitized, root="response")
      self.response.headers['Content-Type'] = "%s; charset=UTF-8" % MIME_XML
      self.response.out.write(xml_str)
      return
    if not path:
      path = self.default_template(ext=base)
    full_path = os.path.join(TEMPLATES_BASE, path)
    if self.file_exists(full_path):
      try:
        # the template might find these handy
        self.response_dict(
          handler=self,
          is_dev=env.is_dev()
        )
        template = get_jinja2_env().get_template(path)
        rendered = template.render(**self.response_dict())
        if self.is_atom() and self.get_status() == 200:
          # for atom
          self.response.headers['Content-Type'] = "%s; charset=UTF-8" % MIME_ATOM
        self.response.out.write(rendered)
      except jinja2.TemplateError, error:
        self.response.headers['Content-Type'] = 'text/plain'
        message = "Template syntax error: %s" % error
        logging.critical(message)
        (error_type, error, tb) = sys.exc_info()
        tb_formatted = traceback.format_tb(tb)
        self.response.out.write("\n".join([message]+tb_formatted))
    elif path is ERROR_HTML:
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write("%s %s" % (self.get_status(), self.get_error()))
    elif path is NOT_FOUND_HTML:
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write("%s %s" % (self.get_status(), 'not found'))
    else:
      logging.critical("Template not found: %s" % path)
      self.render(self.not_found())
  
  def file_exists(self, path):
    return os.path.exists(path)
  
  def redirect(self, uri, *args):
    """Redirects to the given location (in HTML mode)."""
    if self.is_html():
      self._is_redirect = 1
      super(RequestHandler, self).redirect(str(uri), *args)
  
  def not_found(self, status=404):
    """Returns generic not-found template."""
    self.set_status(status=status)
    return NOT_FOUND_HTML
  
  def set_status(self, status):
    """Sets the response status."""
    self.response_dict(status=status)
    self.response.set_status(code=status)
  
  def get_status(self):
    """Returns the response status."""
    response_dict = self.response_dict()
    return response_dict.status
  
  def get_error(self):
    """Returns the response error message if any."""
    response_dict = self.response_dict()
    return response_dict.error
  
  def form_error(self, **kwargs):
    """Set the given form errors."""
    response = self.response_dict()
    for key, value in kwargs.iteritems():
      response.errors[key] = value
    
  def config(self):
    """Returns the local configuration."""
    return local.config()
    
  def environ(self, k=None):
    if k is None:
      return os.environ
    else:
      return os.environ.get(k)
  
  def base_path(self):
    return 'http://%s%s' % (self.host(), self.environ('PATH_INFO'))
  
  def extension(self):
    ext = self.url_arg(-1)
    if ext:
      return '.'+ext
