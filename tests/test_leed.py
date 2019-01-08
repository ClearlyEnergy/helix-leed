"""Test for the LEED module"""
import unittest
import os
import datetime

from leed import leed


class LeedTest(unittest.TestCase):

    def setUp(self):
        self.leed = leed.LeedHelix()

    def test_page_has_score(self):
        result = self.leed.query_leed('/activities/leed-10549162')
        self.assertTrue(result['status'],'success')
        self.assertEqual(result['Green Assessment Property Rating'],'CERTIFIED')
        
    def test_page_was_not_scored(self):
        result = self.leed.query_leed('/activities/leed-10391892')
        self.assertTrue(result['status'],'error')
        self.assertEqual(result['message'],'not rated')

    def test_retrieve_list_for_valid_geo_id(self):
        building_ids = self.leed.query_leed_building_ids('6611')
        self.assertGreater(len(building_ids), 0)

    def test_fail_bad_bulding_id(self):
        result = self.leed.query_leed('/activities/leed-11111111')
        self.assertTrue(result['status'],'error')

    def test_gets_postal_code(self):
        result = self.leed.query_leed('/activities/leed-10549162')
        self.assertTrue(result['Postal Code'],'05403')
