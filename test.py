#!/usr/bin/python
# -*- coding: utf-8 -*-

#
#
#
# Usage:
# 
# Author: rja 
#
# Changes:
# 2017-06-21 (rja)
# - initial version 

from __future__ import print_function
import re
import unittest
from json2json import normalise_page

class TestDNB(unittest.TestCase):
    

    def test_normalise_page(self):
        # | 0 S.       | 902634 |
        self.assertEqual(normalise_page("0 S."), "0")
        self.assertEqual(normalise_page("1234 S."), "1234")
        # | 0 S.;      |  18909 |
        self.assertEqual(normalise_page("1 S.;"), "1")
        self.assertEqual(normalise_page("12 S.;"), "12")
        # | [0] S.     |  18739 |
        self.assertEqual(normalise_page("[1] S."), "1")
        self.assertEqual(normalise_page("[12] S."), "12")
        # | 0 Seiten   |  13436 |
        self.assertEqual(normalise_page("1 Seite"), "1")
        self.assertEqual(normalise_page("12 Seiten"), "12")
        # | 0 Bl.      |  13105 |
        
        # | VIII, 0 S. |   7168 |
        # | XII, 0 S.  |   4224 |
        self.assertEqual(normalise_page("VIII, 1 S."), "1")
        self.assertEqual(normalise_page("XIYI, 12 S."), "12")
        # | 0, [0] S.  |   5758 |
        self.assertEqual(normalise_page("3, [1] S."), "1")
        self.assertEqual(normalise_page("300, [12] S."), "12")
        # | 0, 0 S.    |   4643 |
        self.assertEqual(normalise_page("121, 0 S."), "0")
        self.assertEqual(normalise_page("23, 1234 S."), "1234")

if __name__ == '__main__':
    unittest.main()
