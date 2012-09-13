"""
Created September 6, 2012

@author: Justin Hammond, Rackspace Hosting
"""
import aicq.nvplib as nvp
from aicq import test
from quantum.common import exceptions as exception


class TestBasicUse(test.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        nvp._resetconn()

    def test_except_network(self):
        #TODO: Put this into a test
        with self.assertRaises(exception.QuantumException):
            nvp.get_network("http://nvp", "*")

    def test_fail_network(self):
        #TODO: Put this into a test
        with self.assertRaises(exception.NetworkNotFound):
            nvp.get_network("https://nvp", "*")

    def test_get_network(self):
        #TODO: Put this into a test
        res = nvp.get_network("https://nvp",
                                   "101661a7-b5d1-4ee6-b443-1d81dfaf4b81")
        self.assertIsNotNone(res)
