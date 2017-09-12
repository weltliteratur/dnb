#!/usr/bin/python3
# -*- coding: utf-8 -*-

#
# Computes some text statistics.
#
# Usage:
# 
# Author: rja 
#
# Changes:
# 2017-09-12 (rja)
# - added punctuation cleansing
# - added counting of nouns
# 2017-09-11 (rja)
# - initial version 

version = "0.0.1"

import re
import fileinput
from collections import Counter

re_punct_start = re.compile("^\W+", re.UNICODE)
re_punct_end =   re.compile("\W+$", re.UNICODE)

def get_stopwords(fname):
    stop = set()
    with open(fname, "rt") as f:
        for line in f:
            if line[0:1] == ";":
                next
            stop.add(line.strip())
    return stop

def gen_lines():
    for line in fileinput.input():
        yield line

def gen_text(lines):
    for line in lines:
        year, title = line.strip().split('\t')
        yield title

def gen_words(texts):
    # split
    for text in texts:
        yield text.split(' ')

def clean_words(texts):
    for words in texts:
        result = []
        for word in words:
            clean = clean_word(word)
            if clean != None:
                result.append(clean)
        yield result
        
def clean_word(word):
    # ignore [achtzehn]
    if word[0:1] == "[" and word[-1:] == "]":
        return None
    m = re_punct_start.search(word)
    if m:
        word = word[m.end():]
    m = re_punct_end.search(word)
    if m:
        word = word[:m.start()]
    if word.strip() == "":
        return None
    return word

def print_words(texts):
    for w in texts:
        for ww in w:
            print(ww)

def print_counts(ngrams, nouns, topk, sep='\t'):
    print("*** nouns")
    for val, ct in nouns.most_common(topk):
        print(ct, val, sep=sep)

    for k, count in enumerate(ngrams):
        print("***", k + 1)
        for val, ct in count.most_common(topk):
            print(ct, val, sep=sep)

#stop = get_stopwords('german_stopwords_full.txt')
stop = get_stopwords('/home/rja/nltk_data/corpora/stopwords/german')

def stopwords(words):
    # are all of them stopwords?
    return all([word.lower() in stop for word in words])

def count_ngrams(ngrams, text, n):
    l = len(text)
    for i, p in enumerate(text):
        for k, counts in enumerate(ngrams):
            j = i + k + 1
            if j < l:
                words = text[i:j]
                if not stopwords(words):
                    counts[' '.join(words)] += 1

def count_nouns(nouns, text):
    for word in text:
        # FIXME: isupper() only works for A-Z
        if word.lower() not in stop and word[0:1].isupper():
            nouns[word] += 1
    
def count(texts, n):
    ngrams = [Counter() for k in range(n)]
    nouns = Counter()
    
    for text in texts:
        count_ngrams(ngrams, text, n)
        count_nouns(nouns, text)
        
    return ngrams, nouns

if __name__ == '__main__':

    n = 4
    topk = 20
    
    lines  = gen_lines()
    texts  = gen_text(lines)
    texts  = gen_words(texts)
    texts  = clean_words(texts)

#    print_words(texts)
    
    ngrams, nouns = count(texts, n)

    print_counts(ngrams, nouns, topk)
