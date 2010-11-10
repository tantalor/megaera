"""Accessors for an app's local configuration

The local configuration is loaded from a YAML file. The default
configuration is "local.yaml", in the app's root.

An app's local configuration can change depending on the current
environment, i.e., development and production.

For example,

  pirate: ninja
  robot:
    dev: zombie
    prod: monkey

In development, this app's local config will be,

  {'pirate': 'ninja', 'robot': 'zombie'}

In production, the app's local config will be,

  {'pirate': 'ninja', 'robot': 'monkey'}
"""

import yaml
import os

from env import branch

from google.appengine.api import memcache


def config(filename='local.yaml'):
  """Return the config (dict) for the current environment."""
  cachekey = 'config:%s' % filename
  # check memcache
  try:
    config = memcache.get(cachekey)
    if config:
      return config
  except AssertionError: pass
  if os.path.exists(filename):
    config = yaml.load(file(filename).read())
    # branch each value by environment
    config = dict([(key, branch(value)) for key, value in config.iteritems()])
    try:
      memcache.set(cachekey, config)
    except AssertionError: pass
    return config
  return dict()

def config_get(key):
  """Return the value for the given key from the default config."""
  return config()[key]
