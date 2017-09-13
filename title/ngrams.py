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
# 2017-09-13 (rja)
# - added command line support
# - added duplicate removal
# 2017-09-12 (rja)
# - added punctuation cleansing
# - added counting of nouns
# 2017-09-11 (rja)
# - initial version 

version = "0.0.3"

import re
import argparse
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

def gen_lines(fname):
    with open(fname, "rt", encoding="utf-8") as f:
        for line in f:
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

# remove duplicates
def gen_filter(texts, sep=' '):
    seen = set()
    for text in texts:
        string = ' '.join(text)
        if string not in seen:
            seen.add(string)
            yield text

def print_words(texts):
    for w in texts:
        for ww in w:
            print(ww)

def print_counts(ngrams, nouns, topk, sep):
    print("*** nouns")
    for val, ct in nouns.most_common(topk):
        print(ct, val, sep=sep)

    for k, count in enumerate(ngrams):
        print("***", k + 1)
        for val, ct in count.most_common(topk):
            print(ct, val, sep=sep)

def count_ngrams(ngrams, text, n, stopwords):
    l = len(text)
    for i, p in enumerate(text):
        for k, counts in enumerate(ngrams):
            j = i + k + 1
            if j < l:
                words = text[i:j]
                # all stopwords?
                if not all([word.lower() in stopwords for word in words]):
                    counts[' '.join(words)] += 1

def count_nouns(nouns, text, stopwords):
    for word in text:
        if word.lower() not in stopwords and (word[0:1].isupper() or word[0:1] in ('Ä', 'Ö', 'Ü')):
            nouns[word] += 1
    
def count(texts, n, fstopwords):
    stopwords = get_stopwords(fstopwords)
    ngrams = [Counter() for k in range(n)]
    nouns = Counter()
    
    for text in texts:
        count_ngrams(ngrams, text, n, stopwords)
        count_nouns(nouns, text, stopwords)
        
    return ngrams, nouns

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute text statistics.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('input', type=str, help='input file')
    parser.add_argument('-d', '--deduplicate', action="store_true", help="remove duplicates")
    parser.add_argument('-k', '--topk', type=int, metavar="K", help="print top k results", default=20)
    parser.add_argument('-n', '--ngrams', type=int, metavar="N", help="print n grams for n=1,...,N", default=4)
    parser.add_argument('-s', '--sep', type=str, metavar="S", help="column separator", default='\t')
    parser.add_argument('--stopwords', type=str, metavar="FILE", help="stopword file", default="/home/rja/nltk_data/corpora/stopwords/german")

    args = parser.parse_args()

    lines = gen_lines(args.input)
    texts = gen_text(lines)
    texts = gen_words(texts)
    texts = clean_words(texts)
    if args.deduplicate:
        texts = gen_filter(texts)

#    print_words(texts)
    
    ngrams, nouns = count(texts, args.ngrams, args.stopwords)

    print_counts(ngrams, nouns, args.topk, args.sep)
