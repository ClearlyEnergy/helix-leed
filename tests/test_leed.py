"""Test for the LEED module"""
import unittest
import os
import datetime

from leed import leed


class LeedTest(unittest.TestCase):

    def setUp(self):
        self.leed = leed.LeedHelix()

    def test_page_has_score(self):
        result = self.leed.query_leed('activities/leed-10549162')
        self.assertTrue(result['status'],'success')
        self.assertEqual(result['green_assessment_property_rating'],'Certified')
        
    def test_page_was_not_scored(self):
        result = self.leed.query_leed('/activities/leed-10391892')
        self.assertTrue(result['status'],'error')
        self.assertEqual(result['message'],'not rated')

    def test_retrieve_list(self):
        building_ids = self.leed.query_leed_building_ids()
        self.assertGreater(len(building_ids), 0)

    def test_fail_bad_bulding_id(self):
        result = self.leed.query_leed('activities/leed-11111111')
        self.assertTrue(result['status'],'error')
