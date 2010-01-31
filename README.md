# Megaera

**Megaera** is a python module for [Google App Engine](http://code.google.com/appengine/) applications. It offers a subclass of _[webapp.RequestHandler](http://code.google.com/appengine/docs/python/tools/webapp/requesthandlerclass.html)_ called _Megaera_ with additional functionality.

![Megaera, Tisipone, and Alecto](/dodgeballcannon/megaera/raw/master/megaera.jpg)

## Motivation

The _webapp.RequestHandler_ class lacks several features common to web application frameworks such as automatic rendering of templates and support for alternate output formats (e.g., YAML, JSON).

To solve this, the _Megaera_ class (which bases _webapp.RequestHandler_) associates a "handler" with one or more django templates (e.g., html, atom). Each handler is stored in a distinct file and can respond to a GET or POST request (or both). If the request specifies YAML or JSON output, the handler's response is automatically rendered in the specified type.

The basic Google App Engine SDK also omits common tasks such as distinguishing development and production environments and accessing application-specific local configuration.

Megaera solves these problems together by relying on a single `local.yaml` file in the application's root which can store configuration data for the development and production environments. Megaera's `local.config` function then will automatically load the correct configuration data depending on the application's current environment.

## Tests

Megaera is packaged with [unit tests](http://docs.python.org/library/unittest.html) in the `test/` directory. 
### Example

    $ python test/megaera_test.py
    ........
    ----------------------------------------------------------------------
    Ran 8 tests in 0.002s

    OK
