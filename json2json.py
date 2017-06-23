#!/usr/bin/python3
# -*- coding: utf-8 -*-

#
# Normalise JSON:
# - strip common prefixes for URLs
# - normalise white space
# -
#
# Usage:
#
# Author: rja
#
# Changes:
# 2017-06-21 (rja)
# - initial version

import argparse
import json
import os
import gzip
import re

version = "0.0.1"

# strip the provided prefix from the value of the corresponding key
strip_prefix = {
    # also: http://ld.zdb-services.de/resource/20292-7
    "_id": "http://d-nb.info/",
    "contributor": "http://d-nb.info/gnd/",
    "creator": "http://d-nb.info/gnd/",
    "lang": "http://id.loc.gov/vocabulary/iso639-2/",
    # also: http://iflastandards.info/ns/isbd/terms/mediatype/T1008
    "medium": "http://rdaregistry.info/termList/",
    # also: http://dewey.info/class/684.1005/e22/
    "subject": "http://d-nb.info/gnd/",
    "type": "http://purl.org/ontology/bibo/",
    }

# normalise page specification
# most frequent formats:
# | format     |  count |
# |------------+--------|
# | 0 S.       | 902634 |
# |            | 116585 |
# | 0 S.;      |  18909 |
# | [0] S.     |  18739 |
# | 0 Seiten   |  13436 |
# | 0 Bl.      |  13105 |
# | VIII, 0 S. |   7168 |
# | 0, [0] S.  |   5758 |
# | 0, 0 S.    |   4643 |
# | XII, 0 S.  |   4224 |
#
# find more with: sed "s/[0-9]/0/g" pages | sed "s/00*/0/g" | sort -S4G | uniq -c | sort -nr | less
pages_re = re.compile(r"\[?([0-9]+)\]? S(\.|eiten?);?")
def normalise_page(val):
    m = pages_re.match(val)
    if m:
        return int(m.group(1))
    elif "," in val:
        # match against first part after comma
        m = pages_re.match(val.split(",")[1].strip())
        if m:
            return int(m.group(1))
    return None

def normalise_pages(vals):
    for v in vals:
        vnorm = normalise_page(vals[0])
        if vnorm is not None:
            return vnorm
    return None

# normalise the value for the key using the provided method
norm_set = {
    "pages": normalise_pages
    }

def gen_lines(fpath):
    if os.path.splitext(fpath)[1] == ".gz":
        return gzip.open(fpath, "rt", encoding="utf-8")
    else:
        return open(fpath, "rt", encoding="utf-8")

def gen_items(lines):
    for line in lines:
        yield json.loads(line)

def normalise(items):
    for item in items:
        newvals = {}
        for key in item:
            val = item[key]
            # distinguish between strings and lists
            if isinstance(val, str):
                item[key] = normalise_val(key, val)
            else:
                if key in norm_set:
                    # call dedicated function to convert set to string
                    newvals[key + "_norm"] = norm_set[key](val)
                else:
                    # normalise each value separately
                    item[key] = [normalise_val(key, v) for v in val]
        item.update(newvals)
        yield item

# normalise an individual value
def normalise_val(key, val):
    if key in strip_prefix:
        prefix = strip_prefix[key]
        if val.startswith(prefix):
            return val[len(prefix):]
    return val


def dump(items, key=None):
    for item in items:
        print(json.dumps(item))
        
def dump_cols(items, cols, sep):
    for item in items:
        result = []
        for col in cols:
            if col in item:
                result.append(str(item[col]))
            else:
                result.append("")
        print(sep.join(result))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Normalise JSON.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('input', type=str, help='(gzipped) input RDF file')
    parser.add_argument('-n', '--normalise', action="store_true", help="normalise")
    parser.add_argument('-p', '--print', type=str, metavar="C,D,E,...", help="print columns instead of JSON")
    parser.add_argument('-s', '--sep', type=str, metavar="S", help="column separator", default='\t')
    parser.add_argument('-v', '--version', action="version", version="%(prog)s " + version)

    args = parser.parse_args()

    lines = gen_lines(args.input)
    items = gen_items(lines)
    if args.normalise:
        items = normalise(items)
    if args.print:
        dump_cols(items, args.print.split(","), args.sep)
    else:
        dump(items)
