# Megaera

**Megaera** is a python package which simplifies the creation of [Google App Engine](http://code.google.com/appengine/) applications.

The core component of Megaera is the _megaera.RequestHandler_ class, a subclass of _[webapp.RequestHandler](http://code.google.com/appengine/docs/python/tools/webapp/requesthandlerclass.html)_. This class extends the basic functionality of _webapp.RequestHandler_ to handle common tasks such as creating request handlers, rendering templates, and handling alternate output formats.

![Megaera, Tisipone, and Alecto](https://github.com/tantalor/megaera/raw/master/megaera.jpg)

## Motivation

Google App Engine's _webapp.RequestHandler_ is very powerful, but there are some common features in web applications which it does not handle. It is the developer's responsiblity to add these features.

One common feature is to render a template (e.g., html, atom) after running a request handler. Megaera solves this problem by detecting the correct template to render based on the filesystem location of your request handler.

Megaera also simplifies the process of creating a request handler. Instead of subclassing _webapp.RequestHandler_, your request handlers are simple python modules which implement GET and POST functionality. Megaera handles the job of setting up the application's request handler subclasses for you.

Frequently applications need to serve different output formats, such as JSON. Megaera simplifies this challenge by automatically serving a variety of output formats for every request handler.

Sometimes your application needs to distinguish between the development and production environment. Megaera provides a simple interface which answers this question to all handlers and templates.

Applications might have a lot of local configuration, such as external API keys. Megaera has robust support for local configuration stored in a single file in your application root. You can combine configuration data for development and production environments, and your application will automatically use the correct configuration for the current environment.

## Handling Requests

Suppose you have the following files in your application.

    templates/
      default.html
    handlers/
      __init__.py
      default.py
    main.py
    app.yaml

To get your Megaera app up and running, first add a route in `app.yaml` from all paths to your `main.py`. Put this at the end if your handlers so any static files or other handlers won't be caught by the url regex. This is the default setting for App Engine.

    - url: .*
      script: main.py

In your `main.py`, build your _WSGIApplication_ by routing "/" to a _RequestHandler_  with `RequestHandler.with_page()`. In this case, we are routing "/" to the `handlers.default` module.

    from google.appengine.ext.webapp import WSGIApplication
    from google.appengine.ext.webapp.util import run_wsgi_app
    
    from megaera import RequestHandler
    
    def application():
      return WSGIApplication([
        ('/', RequestHandler.with_page('handlers.default'))
      ], debug=True)
    
    def main():
      run_wsgi_app(application())
    
    if __name__ == "__main__":
      main()

The `handlers.default` module can respond to GET requests very simply by defining a `handlers.default.get()` function which accepts `handler` and `response` arguments. The `handler` argument is a _RequestHandler_ (a _webapp.RequestHandler_). The `response` argument is a special data structure called a _recursivedefaultdict_.

    def get(handler, response):
      name = handler.request.get('name')
      response.messages.hello = "hello %s" % name

A _recursivedefaultdict_ is a _[defaultdict](http://docs.python.org/library/collections.html#collections.defaultdict)_ whose keys can be read/written by the dot operator (i.e., _[getattr](http://docs.python.org/reference/datamodel.html#object.__getattr__)_, _[setattr](http://docs.python.org/reference/datamodel.html#object.__setattr__)_) and whose "default" is another _recursivedefaultdict_. The end result is a very simple-to-use datastructure. Megaera's _recursivedefaultdict_ is based on code samples by [Kent S Johnson](http://personalpages.tds.net/~kent37/kk/00013.html).

Finally, `templates/default.html` is a simple [jinja2](http://jinja.pocoo.org/) template.

    {% if messages %}
      <p>{{messages.hello}}</p>
    {% endif %}
    <p>Your host is {{handler.host()}}.</p>
    {% if is_dev %}
      <p>This is development.</p>
    {% endif %}

Megaera also automatically exposes `handler` (the request handler) and `is_dev` (a boolean) parameters to the templates.

## Caching

Megaera knows how to cache your handler's output. `RequestHandler.cache()` accepts arbitrary keyword parameters to cache indefinitely, keyed by the current handler and with optional `time` time-to-live and `vary` parameters. `RequestHandler.cached()` will return `True` if there exists a cached value for the current handler and optional `vary` parameter.

    def get(handler, response):
      if not handler.cached():
        # cache the following
        foo_data = fetch_foo_from_datastore()
        bar_data = fetch_bar_from_datastore
        # sets response.foo and response.bar
        handler.cache(foo=foo_data, bar=bar_data, time=60)

The `vary` parameter can be used to key the cache by a variable local to the handler such as an object.

## Megaera Configuration

By default, Megaera will guess where your templates are located and what they are named based on the filename of your handler modules. For instance, the `handlers.default` module's template should be `templates/default.html`. If you want to change the handlers or templates directories, just set the `RequestHandler.HANDLERS_BASE` and `RequestHandler.TEMPLATES_BASE` to your desired values in your `main.py`.

## Local Configuration

Megaera will look for an optional local configuration in `local.yaml`.

The structure of the local configuration is a dictionary. Every value of the dictionary may optionally be a dictionary with _prod_ and _dev_ keys. In this case, the _prod_ value will be used in production and the _dev_ value will be used in development.

The local configuration will automatically be cached in memcached.

To load the entire configuration for a given environment, call `local.config()`.

To load a value for a particular key, call `local.config_get(key)`. This will throw a _KeyError_ if the key doesn't exist.

### Example

In this example, the _yahoo_ key has distinct _appId_ values for production and development.

    yahoo:
      prod:
        appId: 7d3a4304887748f01a492daa0a70e770
      dev:
        appid: 89823f9248a5e9408e63d47179f8a8b3

## JSON, YAML, XML, Atom

Any handler's response can be automatically mapped to JSON, YAML, or XML. Any handler with a ".atom" template can also be rendered as Atom. Megaera knows which format to return based on the request's path suffix or query parameters.

For example, the `/foo.yaml` or `/foo?yaml` requests will render your "foo" handler in YAML.

Megaera will try to recursively sanitize the response before returning JSON, YAML, or XML. You should define `sanitize()` methods on your models to return sanitized data for the client.

### XML

Unlike JSON and YAML, arbitrary data structures cannot simply be mapped into XML without making some decisions.

Megaera will map a list to a sequence of elements. If the list is a dictionary value, then the elements be tagged with the dictionary key.

For example, Megaera will render the data structure `{foo: [1, 2]}` in XML as,

    <?xml version="1.0" ?>
    <response>
      <foo>1</foo>
      <foo>2</foo>
    </response>

If the list is not a dictionary value, the elements will be tagged "value".

For example, Megaera will render the data structure `{foo: ["bar", [1, 2]]}` in XML as,

    <?xml version="1.0" ?>
    <reponse>
      <foo>bar</foo>
      <foo>
        <value>1</value>
        <value>2</value>
      </foo>
    </response>

## Error Cases (404, 405, 500, 503)

If you want to deliver a generic "not found" page, just call the `not_found()` method from your handler with an optional HTTP status code, e.g. 404 (Not Found). You can customize this message in `templates/not_found.html`. If the handler cannot respond to the request method then Megaera will respond with a 405 (Method Not Allowed) HTTP status code.

If your handler raises an exception, Megaera will deliver a generic error page with the value of the exception and a 500 (Internal Server Error) HTTP status code. You can customize this message in `template/error.html`. If the exception is a `google.appengine.api.datastore_errors.NeedIndexError` then Megaera will response with a 503 (Service Unavailable) HTTP status code.

## Web Service

Any applications based on Megaera is a [Web service](http://en.wikipedia.org/wiki/Web_service) because it automatically speaks JSON, YAML, XML, and Atom.

Megaera supports GET and POST requests, but not PUT or DELETE, so you likely cannot provide a REST application with Megaera. However, any application which follows the convention of performering writes on (and only on) POST requests might be called [half-REST](http://stereolambda.com/2010/04/21/the-reason-behind-the-half-rest-design-pattern/).

## Tests

Megaera is packaged with [unit tests](http://docs.python.org/library/unittest.html) in the `test/` directory. 
### Example

    megaera$ python test/all.py
    ...................
    ----------------------------------------------------------------------
    Ran 19 tests in 0.007s

    OK
