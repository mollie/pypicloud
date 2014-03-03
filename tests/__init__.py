""" Tests for pypicloud """
from datetime import datetime

from collections import defaultdict
from mock import MagicMock
from pyramid.testing import DummyRequest

from pypicloud.cache import ICache
from pypicloud.models import Package
from pypicloud.storage import IStorage


try:
    import unittest2 as unittest  # pylint: disable=F0401
except ImportError:
    import unittest


def make_package(name='mypkg', version='1.1', filename=None,
                 last_modified=datetime.utcnow(), factory=Package, **kwargs):
    """ Convenience method for constructing a package """
    filename = filename or '%s-%s.tar.gz' % (name, version)
    return factory(name, version, filename, last_modified, **kwargs)


class DummyStorage(IStorage):

    """ In-memory implementation of IStorage """

    def __init__(self, request=None):
        super(DummyStorage, self).__init__(request)
        self.packages = {}

    def __call__(self, *args):
        return self

    def list(self, factory=Package):
        """ Return a list or generator of all packages """
        for args in self.packages.itervalues():
            yield args[0]

    def download_response(self, package):
        return None

    def upload(self, package, data):
        self.packages[package.filename] = (package, data)

    def delete(self, package):
        del self.packages[package.filename]

    def reset(self):
        """ Clear all packages """
        self.packages = {}

    def open(self, package):
        return self.packages[package.filename][1]


class DummyCache(ICache):

    """ In-memory implementation of ICache """
    storage_impl = DummyStorage
    allow_overwrite = False

    def __init__(self, request=None):
        super(DummyCache, self).__init__(request)
        self.packages = defaultdict(dict)

    @classmethod
    def configure(cls, config):
        pass

    def __call__(self, request):
        self.request = request
        self.storage.request = request
        return self

    def reset(self):
        """ Clear all packages from storage and self """
        self.packages.clear()
        self.storage.reset()

    def fetch(self, filename):
        """ Override this method to implement 'fetch' """
        return self.packages.get(filename)

    def all(self, name):
        """ Override this method to implement 'all' """
        return [p for p in self.packages.itervalues() if p.name == name]

    def distinct(self):
        """ Get all distinct package names """
        return list(set((p.name for p in self.packages.itervalues())))

    def clear(self, package):
        """ Remove this package from the caching database """
        del self.packages[package.filename]

    def clear_all(self):
        """ Clear all cached packages from the database """
        self.packages.clear()

    def save(self, package):
        """ Save this package to the database """
        self.packages[package.filename] = package


class MockServerTest(unittest.TestCase):

    """ Base class for tests that need in-memory ICache objects """

    def setUp(self):
        self.request = DummyRequest()
        self.request.registry = MagicMock()
        self.db = self.request.db = DummyCache(self.request)
        self.request.path_url = '/path/'
        self.params = {}
        self.request.param = lambda x: self.params[x]

    def tearDown(self):
        self.request.db.reset()