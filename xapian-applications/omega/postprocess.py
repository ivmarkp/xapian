# Postprocess click data files.
#
# Copyright (C) 2017 Vivek Pal
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
# USA

"""Postprocesses search and clicks data files.

Generates the final clickstream log file and Query file for Xapian Letor
module from that log file.
"""

import argparse
import collections
import csv
import sys


def generate_combined_log(search_log, clicks_log, final_log):
    """Generates the final log file.

    Input Args:
        search_log (str): Path to the search.log file.
        clicks_log (str): Path to the clicks.log file.
        final_log (str): Path to the final.log file.

    Example (comma-delimited) entries in search_log:

    821f03288846297c2cf43c34766a38f7,"book","45,54",0
    d41d8cd98f00b204e9800998ecf8427e,"","".0
    d41d8cd98f00b204e9800998ecf8427e,"",""0
    098f6bcd4621d373cade4e832627b4f6,"test","35,47",0

    Example (comma-delimited) entries in clicks_log:

    821f03288846297c2cf43c34766a38f7,54
    821f03288846297c2cf43c34766a38f7,54
    098f6bcd4621d373cade4e832627b4f6,35

    Example (comma-delimited) entries in final.log:

    QueryID,Query,Hits,Offset,Clicks
    821f03288846297c2cf43c34766a38f7,book,"45,54",0,"45:0,54:2"
    098f6bcd4621d373cade4e832627b4f6,test,"35,47",0,"35:1,47:0"
    """
    QUERYID, QUERY, HITS = 0, 1, 2
    DOCID = 1

    qid_to_clicks = collections.defaultdict(dict)
    did_to_count = {}
    clicklist = []

    with open(clicks_log, 'r') as clicks_f:
        clicks_reader = csv.reader(clicks_f)

        # Build map: qid_to_clicks = {qid: {did: click_count}}
        for row in clicks_reader:
            qid, did = row[QUERYID], row[DOCID]

            did_to_count = qid_to_clicks[qid]

            # Check if did is already present in did_to_count
            if did in did_to_count:
                # Update did_to_count[did]
                did_to_count[did] += 1
            else:
                did_to_count[did] = 1

            qid_to_clicks[qid] = did_to_count

    with open(search_log, 'r') as search_f, open(final_log, 'w+') as final_f:
        search_reader = csv.reader(search_f)
        writer = csv.writer(final_f)

        # Add headers to final log file
        writer.writerow(["QueryID", "Query", "Hits", "Offset", "Clicks"])

        queries = set()

        for row in search_reader:
            # Skip rows with empty Query string
            if row[QUERY] == '':
                continue

            # Avoid duplicate entries
            if row[QUERY] in queries:
                continue

            queries.add(row[QUERY])

            # Convert Hitlist from str to list
            if not row[HITS]:
                hits = []
            else:
                hits = row[HITS]
                hits = hits.strip().split(',')
                row[HITS] = hits

            clicklist = hits[:]

            # Update clicklist with click values stored in map.
            if row[QUERYID] in qid_to_clicks:
                did_to_count = qid_to_clicks[row[QUERYID]]
                for index, did in enumerate(clicklist):
                    if did in did_to_count:
                        clicklist[index] = '%s:%i' % (did, did_to_count[did])
                    else:
                        clicklist[index] = did + ':0'
            else:
                for index, did in enumerate(clicklist):
                    clicklist[index] = did + ':0'

            # Serialise "Hits" and "Clicks"
            row[HITS] = ','.join(row[HITS])
            clicklist = ','.join(clicklist)

            row.append(clicklist)
            writer.writerow(row)


def generate_query_file(final_log, query_file):
    """Generates Query file formatted as per Xapian Letor documentation.

    Input Args:
        final_log (string): Path to final.log file.
        query_file (string): Path to query.txt file.

    Example (tab-delimited) entries in final.log:

    QueryID,Query,Hits,Offset,Clicks
    821f03288846297c2cf43c34766a38f7,book,"45,54",0,"45:0,54:2"
    098f6bcd4621d373cade4e832627b4f6,test,"35,47",0,"35:1,47:0"

    Example (comma-delimited) entries in query.txt:

    821f03288846297c2cf43c34766a38f7,book
    098f6bcd4621d373cade4e832627b4f6,test
    """
    with open(final_log, 'r') as s, open(query_file, 'w+') as w:
        reader = csv.DictReader(s)
        writer = csv.writer(w)

        for row in reader:
            writer.writerow([row['QueryID'], row['Query']])


def test_combined_log():
    test_search_log = 'log-testdata/search.log'
    test_clicks_log = 'log-testdata/clicks.log'
    test_final_log = 'log-testdata/final.log'

    generate_combined_log(test_search_log, test_clicks_log, test_final_log)

    # Test entries in final.log are correct.
    with open(test_final_log, 'r') as final_f:
        reader = csv.reader(final_f)

        # Skip header row.
        next(final_f)

        for i, row in enumerate(reader):
            if i == 0:
                assert row == ['821f03288846297c2cf43c34766a38f7',
                              'book', '45,54', '0', '45:0,54:2'], "Incorrect entry in final.log"
            if i == 1:
                assert row == ['098f6bcd4621d373cade4e832627b4f6',
                              'test', '35,47', '0', '35:1,47:0'], "Incorrect entry in final.log"

def test_query_file():
    test_final_log = 'log-testdata/final.log'
    test_query_file = 'log-testdata/query.txt'

    generate_query_file(test_final_log, test_query_file)

    # Test entries in query.txt are correct.
    with open(test_query_file, 'r') as query_f:
        reader = csv.reader(query_f)

        for i, row in enumerate(query_f):
            if i == 0:
                assert row == '821f03288846297c2cf43c34766a38f7,book\n', "Incorrect entry in query.txt"
            if i == 1:
                assert row == '098f6bcd4621d373cade4e832627b4f6,test\n', "Incorrect entry in query.txt"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='''Postprocess click data files.

        This script generates the final clickstream log file from input search and
        click log files and creates Query file that can be used by Xapian Letor
        module for generating its training files.
        ''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("search_log", type=str, help="Path to the search.log file.")
    parser.add_argument("clicks_log", type=str, help="Path to the clicks.log file.")
    parser.add_argument("final_log", type=str, help="Path to save final.log file.")
    parser.add_argument("query_file", type=str, help="Path to save query.txt file.")
    parser.add_argument("--test", help="Run tests for this script.", action='store_true')
    args = parser.parse_args()

    try:
        generate_combined_log(args.search_log, args.clicks_log, args.final_log)
        generate_query_file(args.final_log, args.query_file)
    except IOError as e:
        print(e, file=sys.stderr)

    if args.test:
        test_combined_log()
        test_query_file()