#!/usr/bin/python3
# -*- coding: utf-8 -*-

#
# Normalise JSON:
# - strip common prefixes for URLs
# - normalise date
#
# Usage:
#
# Author: rja
#
# Changes:
# 2017-08-23 (rja)
# - refactored and added support to prune rows with empty columns
# 2017-08-22 (rja)
# - added nested path and wildcard support for column selection (-p)
# 2017-08-18 (rja)
# - added normalisation of "issued"
# - added use of "extent" if no pages could be found
# - added Wikidata enrichment
# 2017-06-23 (rja)
# - added comments
# - ignoring None values for new normalised values
# - added parameter -e to enclose each item by {"index": ... }
# 2017-06-21 (rja)
# - initial version

version = "0.0.4"

import argparse
import json
import os
import gzip
import re


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

year_re = re.compile(r"^\s*([0-9]{4})\s*$")
def normalise_issued(val):
    m = year_re.match(val)
    if m:
        return int(m.group(1))
    return None

# create a new normalised value from several values
normalise_many_to_new = {
    "pages": normalise_pages,
    }

# create a new normalised value from one value
normalise_one_to_new = {
    "issued": normalise_issued
}

def gen_lines(fpath):
    if os.path.splitext(fpath)[1] == ".gz":
        return gzip.open(fpath, "rt", encoding="utf-8")
    else:
        return open(fpath, "rt", encoding="utf-8")

def gen_items(lines):
    for line in lines:
        yield json.loads(line)

def gen_elastic(items):
    for item in items:
        yield {"index" : item}

def normalise(items):
    for item in items:
        newvals = {} # additional values
        for key in item:
            val = item[key]
            # separate handling for strings and lists
            if isinstance(val, str):
                if key in normalise_one_to_new:
                    # create a new normalised value
                    newval = normalise_one_to_new[key](val)
                    if newval:
                        newvals[key + "_norm"] = newval
                else:
                    # strings are replaced by their normalised value
                    item[key] = normalise_val(key, val)
            else:
                # either normalise individual list items or add new value
                if key in normalise_many_to_new:
                    # call dedicated function to convert set to string
                    newval = normalise_many_to_new[key](val)
                    if newval:
                        newvals[key + "_norm"] = newval
                else:
                    # normalise each value separately
                    item[key] = [normalise_val(key, v) for v in val]
        # separate handling for extent and page
        if "extent" in item and "pages_norm" not in newvals:
            newvals["pages_norm"] = normalise_page(item["extent"])
        # update after iteration to not break iteration
        item.update(newvals)
        yield item

# reads Wikidata data for creators from Java-generated JSON file
def get_wikidata(wikidata):
    return json.load(open(wikidata, "rt"))

# add data from Wikidata
def enrich(items, wikidata):
    wd = get_wikidata(wikidata)
    for item in items:
        if "creator" in item:
            for creator in item["creator"]:
                if creator in wd:
                    # if required, create new property
                    if "creator_wd" not in item:
                        item["creator_wd"] = {}
                    # add content for each creator using the GND id (= creator)
                    item["creator_wd"][creator] = wd[creator]
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

# select the provided paths as columns
def gen_cols(items, pathspecs):
    for item in items:
        yield [to_str(get_value(item, pathspec.split("."))) for pathspec in pathspecs]

def gen_filter(items):
    for item in items:
        if all([val != "" for val in item]):
            yield item

# print columns as specified by cols (comma-separated list)
def dump_cols(items, sep):
    for item in items:
        print(sep.join(item))

# string conversion supporting lists
def to_str(val):
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return ", ".join(val)
    return str(val)

# retrieves values for nested paths using "." as delimiter and "*" as wildcard
def get_value(item, pathspec):
    # recursive graph traversal
    # destination reached (path empty) -> return current node
    if len(pathspec) == 0:
        return item
    # get next path element
    p = pathspec.pop(0)
    # descend
    if p in item:
        return get_value(item[p], pathspec)
    elif p == "*":
        # handle wildcard: descend into all child nodes
        return ", ".join([to_str(get_value(item[pp], list(pathspec))) for pp in item])
    else:
        # not found
        return ""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Normalise JSON.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('input', type=str, help='(gzipped) input RDF file')
    parser.add_argument('-n', '--normalise', action="store_true", help="normalise")
    parser.add_argument('-e', '--elastic', action="store_true", help="add JSON for Elastic")
    parser.add_argument('-f', '--filter', action="store_true", help="filter rows with empty columns")
    parser.add_argument('-p', '--print', type=str, metavar="C,D,E,...", help="print columns for given paths instead of JSON")
    parser.add_argument('-s', '--sep', type=str, metavar="S", help="column separator for --print", default='\t')
    parser.add_argument('-w', '--wikidata', type=str, metavar="F", help="enrich with Wikidata")
    parser.add_argument('-v', '--version', action="version", version="%(prog)s " + version)

    args = parser.parse_args()

    lines = gen_lines(args.input)
    items = gen_items(lines)
    if args.normalise:
        items = normalise(items)
    if args.wikidata:
        items = enrich(items, args.wikidata)
    if args.print:
        items = gen_cols(items, args.print.split(","))
        if args.filter:
            items = gen_filter(items)
        dump_cols(items, args.sep)
    else:
        if args.elastic:
            items = gen_elastic(items)
        dump(items)
