#!/usr/bin/python3
# -*- coding: utf-8 -*-

#
# Convert DNB RDF/XML to JSON
#
# Usage:
#
# Author: rja
#
# Changes:
# 2017-09-04 (rja)
# - added extraction of rdau:P60493 property to "P60493"
# 2017-06-19 (rja)
# - initial version

import xml.sax
import gzip
import argparse
import os.path
import json

version = "0.0.2"

# SAX parser collecting items
class DNBHandler(xml.sax.ContentHandler):
    # func will be called whenever an item is complete with the item as argument
    def __init__(self, func):
        self.consume = func
        self.item = None
        self.descriptionDepth = 0
        self.chars = ""

        # retrieve content from the rdf:resource attribute of the tag
        self.attr_map = {
            "dcterms:contributor" : "contributor",
            "dcterms:creator" : "creator",
            "dcterms:language" : "lang",
            "dcterms:medium" : "medium",
            "dcterms:subject" : "subject",
            "rdf:type" : "type",
        }
        # retrieve content from the characters between the opening and closing tag
        self.chars_map = {
            "bibo:shortTitle" : "short_title",
            "dc:publisher" : "publisher",
            "dc:title" : "title",
            "dcterms:extent" : "extent",
            "dcterms:issued" : "issued",
            "isbd:P1053" : "pages",
            "rdau:P60001" : "price",
            "rdau:P60163" : "place",
            "rdau:P60333" : "place_publisher",
            "rdau:P60493" : "P60493"
            }
        # create lists for those keys
        self.multi = set(["creator", "contributor", "place", "subject", "pages"])

    def startElement(self, name, attrs):
        if name == "rdf:Description":
            # We have nested rdf:Description tags which we need to avoid -
            # so we only extract data from tags at level 1.
            self.descriptionDepth += 1
            if self.descriptionDepth == 1:
                # new item found
                self.item = {"_id" : attrs.getValue("rdf:about")}
        elif self.descriptionDepth == 1 and name in self.attr_map and "rdf:resource" in attrs:
            # handle generic tags
            self._add(self.attr_map[name], attrs.getValue("rdf:resource"))

    def endElement(self, name):
        if name == "rdf:Description":
            self.descriptionDepth -= 1
            if self.descriptionDepth == 0:
                self.consume(self.item)
        elif name in self.chars_map:
            # handle generic tags
            self._add(self.chars_map[name], self.chars)
        self.chars = ""

    def _add(self, key, val):
        # add basic normalisation
        val = val.strip()
        if key in self.multi:
            # handle keys with multiple values
            if key in self.item:
                self.item[key].append(val)
            else:
                self.item[key] = [val]
        else:
            self.item[key] = val

    def characters(self, content):
        # collect character data between opening and closing tag
        self.chars += content

def get_file(fpath):
    if os.path.splitext(fpath)[1] == ".gz":
        return gzip.open(fpath, "rt", encoding="utf-8")
    else:
        return open(fpath, "rt", encoding="utf-8")

def process(fpath, func):
    parser = xml.sax.make_parser()
    parser.setContentHandler(DNBHandler(func))
    parser.parse(get_file(fpath))

def rdf2json(rdf):
    print(json.dumps(rdf))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert DNB RDF to Elastic JSON.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('input', type=str, help='(gzipped) input RDF file')
    parser.add_argument('-v', '--version', action="version", version="%(prog)s " + version)

    args = parser.parse_args()

    process(args.input, rdf2json)
