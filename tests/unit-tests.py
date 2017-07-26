#!/usr/bin/env python
import os
import sys
import logging
import argparse
import unittest
import cigar as cigarlib
# Path hack to make sure the local pyBamParser loads before the installed version.
script_dir = os.path.dirname(os.path.realpath(__file__))  # .
lib_path = os.path.join(os.path.dirname(script_dir), 'lib')  # ../lib
sys.path.insert(0, lib_path)
from pyBamParser.read import BAMRead

ARG_DEFAULTS = {'log':sys.stderr, 'volume':logging.WARNING}
DESCRIPTION = """Run unit(ish) tests."""


def make_argparser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.set_defaults(**ARG_DEFAULTS)
    parser.add_argument('-l', '--log', type=argparse.FileType('w'),
        help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
    parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL)
    parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
    parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
    return parser


def main(argv):
    parser = make_argparser()
    args = parser.parse_args(argv[1:])
    logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
    for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
        level_name = logging.getLevelName(level)
        logging.addLevelName(level, level_name.capitalize())
    unittest.main()

"""
# Find an example of a type of CIGAR string:
$ samtools view duplex.down10.bam | awk '! and($2, 16) && $3 == "chrM" && $6 ~ /^[0-9]*M[0-9]*S$/ {print $6}' | sort | uniq -c | sort -g -k 1 | head
# Get the rest of the info for the alignment:
$ samtools view duplex.down10.bam | awkt '! and($2, 16) && $3 == "chrM" && $6 == "255M12S"' | cut -f -8
# Check the name is unique:
$ samtools view duplex.down10.bam | grep AACCCAAGTGACTGCTCGCACTTA | wc -l
# Try converting some coordinates:
$ samtools view duplex.down10.bam | grep AACCCAAGTGACTGCTCGCACTTA | ./cigar.py 255
"""

class CigarTest(unittest.TestCase):

    @classmethod
    def get_blocks(cls, pos, cigar, flags, readlen):
        cigar_list = cigarlib.split_cigar(cigar)
        blocks = BAMRead._get_contiguous_blocks(pos, cigar_list, flags & 16, readlen)
        logging.info(blocks)
        return blocks

    @classmethod
    def make_tests(cls):
        for data in cls.test_data:
            test_function = cls.make_test(**data)
            setattr(cls, 'test_'+data['name'], test_function)


class CigarConversionTest(CigarTest):

    @classmethod
    def make_test(cls, name=None, pos=None, cigar=None, flags=None, readlen=None, in_out_pairs=None):
        def test(self):
            blocks = CigarTest.get_blocks(pos, cigar, flags, readlen)
            for read_coord, ref_coord in in_out_pairs:
                result = BAMRead._to_ref_coord(blocks, read_coord)
                try:
                    self.assertEqual(ref_coord, result)
                except AssertionError:
                    logging.warn('Failed {}: {} -> {} (got {} instead)'
                                 .format(cigar, read_coord, ref_coord, result))
                    raise
        return test

    test_data = (
        {'name':'basic', 'pos':781, 'cigar':'284M', 'flags':163, 'readlen':284,
         'in_out_pairs':((0, None), (1, 781), (2, 782), (284, 1064), (285, None))},
        {'name':'insertion', 'pos':8112, 'cigar':'159M9I115M', 'flags':99, 'readlen':283,
         'in_out_pairs':((159, 8270), (160, None), (168, None), (169, 8271))},
        {'name':'deletion', 'pos':2995, 'cigar':'111M1D172M', 'flags':99, 'readlen':283,
         'in_out_pairs':((111, 3105), (112, 3107))},
        {'name':'left_soft_padding', 'pos':5059, 'cigar':'11S267M', 'flags':99, 'readlen':278,
         'in_out_pairs':((11, None), (12, 5059), (13, 5060))},
        {'name':'right_soft_padding', 'pos':6274, 'cigar':'255M12S', 'flags':163, 'readlen':267,
         'in_out_pairs':((255, 6528), (256, None))},
        {'name':'reverse', 'pos':6022, 'cigar':'286M', 'flags':83, 'readlen':286,
         'in_out_pairs':((1, 6307), (2, 6306), (3, 6305), (286, 6022))},
        {'name':'reverse_insertion', 'pos':8027, 'cigar':'248M9I25M', 'flags':83, 'readlen':282,
         'in_out_pairs':((1, 8299), (25, 8275), (26, None), (34, None), (35, 8274))},
        {'name':'reverse_deletion', 'pos':2840, 'cigar':'266M1D17M', 'flags':83, 'readlen':283,
         'in_out_pairs':((1, 3123), (2, 3122), (17, 3107), (18, 3105))},
        {'name':'reverse_deletion_toy', 'pos':1001, 'cigar':'100M100D100M', 'flags':83, 'readlen':200,
         'in_out_pairs':((1, 1300), (100, 1201), (101, 1100), (200, 1001))},
        # The following are taken from Figure 1 of Li et al. 2009 which introduced the SAM format.
        {'name':'Li_r001p', 'pos':7, 'cigar':'8M2I4M1D3M', 'flags':163, 'readlen':17,
         'in_out_pairs':((1, 7), (8, 14), (9, None), (10, None), (11, 15), (14, 18), (15, 20))},
        {'name':'Li_r002p', 'pos':9, 'cigar':'3S6M1P1I4M', 'flags':0, 'readlen':14,
         'in_out_pairs':((1, None), (3, None), (4, 9), (9, 14), (10, None), (11, 15), (14, 18))},
        {'name':'Li_r003p', 'pos':9, 'cigar':'5H6M', 'flags':0, 'readlen':6,
         'in_out_pairs':((0, None), (1, 9), (6, 14), (7, None))},
        {'name':'Li_r004p', 'pos':16, 'cigar':'6M14N5M', 'flags':0, 'readlen':11,
         'in_out_pairs':((1, 16), (6, 21), (7, 36), (11, 40))},
        {'name':'Li_r003n', 'pos':29, 'cigar':'6H5M', 'flags':16, 'readlen':5,
         'in_out_pairs':((1, 33), (5, 29))},
        {'name':'Li_r001n', 'pos':37, 'cigar':'9M', 'flags':83, 'readlen':9,
         'in_out_pairs':((1, 45), (9, 37))}
    )

CigarConversionTest.make_tests()


class CigarGetIndelsTest(CigarTest):

    @classmethod
    def make_test(cls, name=None, pos=None, cigar=None, flags=None, readlen=None, expected=None):
        def test(self):
            blocks = CigarTest.get_blocks(pos, cigar, flags, readlen)
            indels = BAMRead._get_indels(blocks, flags & 16)
            self.assertEqual(indels, expected)
        return test

    test_data = (
        {'name':'M', 'pos':1, 'cigar':'251M', 'flags':99, 'readlen':251,
         'expected':([], [])},
        {'name':'SM', 'pos':1, 'cigar':'3S248M', 'flags':99, 'readlen':251,
         'expected':([], [])},
        {'name':'MS', 'pos':111, 'cigar':'205M46S', 'flags':163, 'readlen':251,
         'expected':([], [])},
        {'name':'MIMr1', 'pos':2, 'cigar':'4M2I245M', 'flags':147, 'readlen':251,
         'expected':([(5, 2)], [])},
        {'name':'MIMr2', 'pos':199, 'cigar':'112M1I138M', 'flags':83, 'readlen':251,
         'expected':([(310, 1)], [])},
        {'name':'MDM', 'pos':2941, 'cigar':'166M1D85M', 'flags':99, 'readlen':251,
         'expected':([], [(3106, 1)])},
        {'name':'MDMr', 'pos':1785, 'cigar':'116M1D135M', 'flags':83, 'readlen':251,
         'expected':([], [(1900, 1)])},
        {'name':'SMS', 'pos':1, 'cigar':'10S156M85S', 'flags':163, 'readlen':251,
         'expected':([], [])},
        {'name':'SMDMr', 'pos':2526, 'cigar':'11S3M1D237M', 'flags':83, 'readlen':251,
         'expected':([], [(2528, 1)])},
        {'name':'SMIMr', 'pos':554, 'cigar':'38S3M3I207M', 'flags':83, 'readlen':251,
         'expected':([(556, 3)], [])},
        {'name':'MDMS', 'pos':2883, 'cigar':'224M1D26M1S', 'flags':163, 'readlen':251,
         'expected':([], [(3106, 1)])},
        {'name':'MIMS', 'pos':4099, 'cigar':'171M1I11M68S', 'flags':99, 'readlen':251,
         'expected':([(4269, 1)], [])},
        {'name':'MIMDM', 'pos':14640, 'cigar':'241M2I3M2D5M', 'flags':163, 'readlen':251,
         'expected':([(14880, 2)], [(14883, 2)])},
        {'name':'MIMIMr', 'pos':16365, 'cigar':'205M39I4M2I1M', 'flags':83, 'readlen':251,
         'expected':([(16573, 2), (16569, 39)], [])},
        {'name':'MIMDMS1', 'pos':9931, 'cigar':'242M1I3M2D2M3S', 'flags':99, 'readlen':251,
         'expected':([(10172, 1)], [(10175, 2)])},
        {'name':'MIMDMS2', 'pos':16390, 'cigar':'179M62I2M2D2M6S', 'flags':99, 'readlen':251,
         'expected':([(16568, 62)], [(16570, 2)])},
        {'name':'SMDMDMr', 'pos':6800, 'cigar':'3S7M1D1M1D240M', 'flags':147, 'readlen':251,
         'expected':([], [(6808, 1), (6806, 1)])},
        {'name':'SMIMIMr', 'pos':5975, 'cigar':'10S5M1I1M1I233M', 'flags':83, 'readlen':251,
         'expected':([(5980, 1), (5979, 1)], [])},
        {'name':'MIMIMS', 'pos':11127, 'cigar':'222M3I6M2I5M13S', 'flags':163, 'readlen':251,
         'expected':([(11348, 3), (11354, 2)], [])},
        {'name':'SMDMIMr', 'pos':6109, 'cigar':'66S2M1D9M1I173M', 'flags':83, 'readlen':251,
         'expected':([(6120, 1)], [(6110, 1)])},
        {'name':'SMIMDMr', 'pos':7603, 'cigar':'12S2M1I1M2D235M', 'flags':83, 'readlen':251,
         'expected':([(7604, 1)], [(7605, 2)])},
        {'name':'MDMIMDMS', 'pos':1, 'cigar':'199M1D2M2I8M2D2M38S', 'flags':99, 'readlen':251,
         'expected':([(202, 2)], [(199, 1), (210, 2)])},
        {'name':'SMDMDMDMr', 'pos':10517, 'cigar':'32S6M1D4M1D2M1D207M', 'flags':147, 'readlen':251,
         'expected':([], [(10530, 1), (10527, 1), (10522, 1)])},
        {'name':'MIMIMDMS', 'pos':13388, 'cigar':'218M2I9M1I1M2D11M9S', 'flags':163, 'readlen':251,
         'expected':([(13605, 2), (13614, 1)], [(13615, 2)])},
    )

CigarGetIndelsTest.make_tests()


class CigarIndelAtTest(CigarTest):

    @classmethod
    def make_test(cls, name=None, pos=None, cigar=None, flags=None, readlen=None, in_out_pairs=None):
        def test(self):
            blocks = CigarTest.get_blocks(pos, cigar, flags, readlen)
            insertions, deletions = BAMRead._get_indels(blocks, flags & 16)
            for pair in in_out_pairs:
                indel_at = BAMRead._indel_at(pair['coord'],
                                             insertions,
                                             deletions,
                                             check_insertions=pair['check_ins'],
                                             check_deletions=pair['check_del'])
                self.assertEqual(indel_at, pair['result'])
        return test

    test_data = (
        {'name':'M', 'pos':31, 'cigar':'251M', 'flags':163, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'MS', 'pos':111, 'cigar':'205M46S', 'flags':163, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SM', 'pos':1, 'cigar':'3S248M', 'flags':99, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SM', 'pos':1, 'cigar':'52S199M', 'flags':99, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'MIM', 'pos':199, 'cigar':'112M1I138M', 'flags':83, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SMS', 'pos':1, 'cigar':'10S156M85S', 'flags':163, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SMDM', 'pos':2526, 'cigar':'11S3M1D237M', 'flags':83, 'readlen':251, 'in_out_pairs':(
            {'coord':1901, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SMIM', 'pos':554, 'cigar':'38S3M3I207M', 'flags':83, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'MIMDM', 'pos':14640, 'cigar':'241M2I3M2D5M', 'flags':163, 'readlen':251, 'in_out_pairs':(
            {'coord':13605, 'result':True, 'check_ins':True, 'check_del':False},
        )},
        {'name':'MIMIM', 'pos':16365, 'cigar':'205M39I4M2I1M', 'flags':83, 'readlen':251, 'in_out_pairs':(
            {'coord':14885, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'MIMDMS', 'pos':9931, 'cigar':'242M1I3M2D2M3S', 'flags':99, 'readlen':251, 'in_out_pairs':(
            {'coord':7606, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SMDMDM', 'pos':6800, 'cigar':'3S7M1D1M1D240M', 'flags':147, 'readlen':251, 'in_out_pairs':(
            {'coord':6111, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SMDMIM', 'pos':6109, 'cigar':'66S2M1D9M1I173M', 'flags':83, 'readlen':251, 'in_out_pairs':(
            {'coord':6111, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'SMIMDM', 'pos':7603, 'cigar':'12S2M1I1M2D235M', 'flags':83, 'readlen':251, 'in_out_pairs':(
            {'coord':6809, 'result':True, 'check_ins':False, 'check_del':True},
        )},
        {'name':'MDMIMDMS', 'pos':1, 'cigar':'199M1D2M2I8M2D2M38S', 'flags':99, 'readlen':251, 'in_out_pairs':(
            {'coord':200, 'result':True, 'check_ins':False, 'check_del':True},
            {'coord':202, 'result':True, 'check_ins':True, 'check_del':False},
            {'coord':211, 'result':True, 'check_ins':True, 'check_del':True},
            {'coord':212, 'result':True, 'check_ins':False, 'check_del':True},
        )},
    )

CigarIndelAtTest.make_tests()


def logging_setup():
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING, format='%(message)s')
    for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
        level_name = logging.getLevelName(level)
        logging.addLevelName(level, level_name.capitalize())


if __name__ == '__main__':
  main(sys.argv)
