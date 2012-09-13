"""
Created: August 27, 2012

@author: Justin Hammond, Rackspace Hosting
"""
import sys

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest


class TestCase(unittest.TestCase):
    pass
