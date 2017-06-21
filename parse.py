#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import rdflib
import gzip
from rdflib.namespace import DCTERMS, DC

# read Wikidata GND ids of writers
writers = set()
with open('wd_result', 'r') as f:
    for line in f:
        entity, gndid = line.strip().split()
        writers.add(gndid)

# read DNB data
g = rdflib.Graph()
g.parse(gzip.open('DNBTitel.ttl.gz', 'rt'), format='n3')
isbd = rdflib.Namespace("http://iflastandards.info/ns/isbd/elements/")

fout = open('dnb_pages.tsv', 'wt')

for s, o in g.subject_objects(DCTERMS["creator"]):
    # property with linked GND id found, extract GND id
    url, gndid = o.rsplit('/', 1)
    # check whether this is a writer
    if gndid in writers:
        # get title and page number
        title = g.value(s, DC["title"], None)
        pages = g.value(s, isbd["P1053"], None)
        print(s, gndid, title.encode("utf-8"), pages, sep='\t', file=fout)

fout.close()
