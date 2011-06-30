#!/usr/bin/env python
#
# bibfile_utils.py: Functions to process the content of bib-files.
#
# Copyright 2011 James Boyden <jboy@jboy.id.au>
#
# This file is part of Distil.
#
# Distil is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License, version 3, as
# published by the Free Software Foundation.
#
# Distil is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License,
# version 3, for more details.
#
# You should have received a copy of the GNU General Public License,
# version 3, along with this program; if not, see
# http://www.gnu.org/licenses/gpl-3.0.html


import sys
import string
import codecs
import re

from bibliograph_parsing_improved import bibtex

import test_framework
import unicode_string_utils


### Errors that may be thrown by this module.


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class ContainsUnicode(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return "file '%s' contains Unicode characters" % self.fname


class InvalidFormat(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return "file '%s' is not in the BibTeX format" % self.fname


class FormatError(Error):
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return self.message


class IncompleteImplementation(Error):
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return self.message


### These are the public functions of the exported API.


def replace_cite_key_in_file(new_cite_key, in_fname, out_fname=None):
  """Assumes that 'in_fname' contains only one BibTeX entry.

  If 'out_fname' is not supplied, or is None, 'out_fname' will be the same as
  'in_fname'.
  """
  if not out_fname:
    out_fname = in_fname

  # Handle possibly-screwed Unicode strings.
  # 's' will now be a Unicode string.
  (s, contains_non_ascii, errors) = unicode_string_utils.open_file_read_unicode(in_fname)

  obj = re.compile('^(@[^@{]+{)[^,]+,')
  if not obj.match(s):
    raise InvalidFormat(in_fname)
  s = obj.sub(r'\1%s,' % new_cite_key, s, 1)

  # Write 's' back out in UTF-8, in case it contains any non-ASCII code-points.
  codecs.open(out_fname, 'w', encoding="utf-8-sig").write(s)


def suggest_cite_keys_for_entries_in_file(fname):
  return suggest_cite_keys_for_entries(read_entries_from_file(fname))


def read_entries_from_file(fname, should_complain_about_non_ascii=True):
  #s = open(fname).read()
  # Handle possibly-screwed Unicode strings.
  # 's' will now be a Unicode string.
  (s, contains_non_ascii, errors) = unicode_string_utils.open_file_read_unicode(fname)
  if contains_non_ascii and should_complain_about_non_ascii:
    complain_about_non_ascii(fname)

  b = bibtex.BibtexParser()

  # The method 'checkFormat' complains about some situations (like a space
  # after "@incollection" or "@article", before the left-brace) that seem to
  # present no problems to 'getEntries'.
  #
  # It also complains about any non-ASCII characters in the string, whether
  # you've opened the file using the built-in 'open' function (which returns
  # a regular string containing UTF-8 characters) or using the 'codecs.open'
  # function with the encoding specified as either "utf-8" or "utf-8-sig"
  # (which returns a Unicode string containing Unicode code-points).
  #
  # Hence, we'll attempt to gloss over any limitations of 'checkFormat' before
  # we invoke it.
  if contains_non_ascii:
    # Temporarily convert any non-ASCII characters to an ASCII character that's
    # not one of the BibTeX syntax characters) and check.
    if not b.checkFormat(gloss_over_checkFormat_limitations(
        unicode_string_utils.replace_non_ascii_unicode(s))):
      raise InvalidFormat(fname)
  else:
    if not b.checkFormat(gloss_over_checkFormat_limitations(s)):
      raise InvalidFormat(fname)

  # The 'preprocess' method will accept either Unicode strings or regular
  # strings, and will always return a regular string (with any Unicode
  # code-points encoded as UTF-8, just as the built-in 'open' function would
  # return).  For example, u'\u2019', the Unicode code-point for "RIGHT SINGLE
  # QUOTATION MARK" will be encoded as '\xe2\x80\x99'.
  #
  # If you invoke 'preprocess' before the 'getEntries' method, 'getEntries'
  # won't have any Unicode problems.
  s = b.preprocess(s)

  # The 'getEntries' method doesn't like to accept Unicode strings, only
  # regular strings (although it's not unhappy if the regular strings contain
  # UTF-8 characters).  If you give it a UnicodeString, it raises a TypeError
  # to complain:
  #
  # File ".../bibliograph/parsing/parsers/base.py", line 134, in getEntries
  #   source = self.checkEncoding(source)
  # File ".../bibliograph/parsing/parsers/base.py", line 143, in checkEncoding
  #   source = unicode(source, 'utf-8')
  # TypeError: decoding Unicode is not supported
  #
  # Hence, we invoke the 'preprocess' method first, to ensure that 'getEntries'
  # won't have any Unicode problems.
  entries = b.getEntries(s)

  return entries


def suggest_cite_keys_for_entries(entries):
  cite_keys = []
  for e in entries:
    ck = suggest_cite_key(e)
    cite_keys.append((ck, e))

  return cite_keys


def suggest_cite_key(bib_entry):
  # FIXME:  Extract 'N' out into the 'constants' module.
  N = 3

  components = [
    get_author_or_editor_surnames(bib_entry),
    get_year(bib_entry),
    get_first_N_words_of_title(bib_entry, N)
  ]
  return "-".join(components)


### Anything below this point is not part of the exported API.


def gloss_over_checkFormat_limitations(s):
  checkFormat_limitations = [
    (r"^(@[^@{ ]+)\s+{", r"\1{"),  # whitespace before brace
  ]
  for pattern, repl in checkFormat_limitations:
    s = re.sub(pattern, repl, s)

  return s


def complain_about_non_ascii(in_fname):
  print >> sys.stderr, \
      "Warning: file '%s' contains non-ASCII Unicode code-points." % \
      in_fname


def get_author_or_editor_surnames(bib_entry):
  if not bib_entry.has_key("authors"):
    raise IncompleteImplementation(
        "Unable to find 'authors' key in parsed BibTeX entry '%s'" %
        bib_entry["pid"])

  authors = bib_entry["authors"]
  if len(authors) == 0:
    raise FormatError(
        "Empty 'authors' list in parsed BibTeX entry '%s'" %
        bib_entry["pid"])
  elif len(authors) == 1:
    return normalise_name(authors[0])
  elif len(authors) == 2:
    return "%s-%s" % (normalise_name(authors[0]), normalise_name(authors[1]))
  else:
    return "%s-etal" % normalise_name(authors[0])


def normalise_name(author):
  return normalise_lastname(author["lastname"])


def normalise_lastname(lastname):
  # This function exists (separate from 'normalise_name') to enable testing.
  # FIXME:  Extract this value 7 out into the 'constants' module.
  return normalise_to_ascii_lower(lastname)[:7]


def normalise_to_ascii_lower(s):
  # Note that we invoke 'transliterate_to_ascii' before 'strip_punctuation_and_whitespace'
  # because 'transliterate_to_ascii' may well introduce some punctuation or whitespace
  # which we then want 'strip_punctuation_and_whitespace' to remove.
  return strip_punctuation_and_whitespace(
      unicode_string_utils.transliterate_to_ascii(s)).lower()


STRIP_PUNCTUATION_AND_WHITESPACE = \
    unicode_string_utils.StripPunctuationAndWhitespace()

def strip_punctuation_and_whitespace(s):
  return STRIP_PUNCTUATION_AND_WHITESPACE(s)


def get_year(bib_entry):
  if bib_entry.has_key("year"):
    return ensure_year_is_number(bib_entry, "year")
  elif bib_entry.has_key("YEAR"):
    return ensure_year_is_number(bib_entry, "YEAR")
  else:
    raise IncompleteImplementation(
        "Unable to find 'year' or 'YEAR' key in parsed BibTeX entry '%s'" %
        bib_entry["pid"])


def ensure_year_is_number(bib_entry, key):
  value = bib_entry[key]
  try:
    int(value)
  except ValueError:
    raise FormatError(
      "Value of '%s' key ('%s') is not a valid number in parsed BibTeX entry '%s'" %
      (key, value, bib_entry["pid"]))

  return value


def get_first_N_words_of_title(bib_entry, N):
  if bib_entry.has_key("title"):
    return normalise_first_N_words_of_title(bib_entry["title"], N)
  elif bib_entry.has_key("TITLE"):
    return normalise_first_N_words_of_title(bib_entry["TITLE"], N)
  else:
    raise IncompleteImplementation(
        "Unable to find 'title' or 'TITLE' key in parsed BibTeX entry '%s'" %
        bib_entry["pid"])


# All words of less than 3 characters will be blocked automatically.
# Words such as "approach" and "experiment" are uninformative (and interchangeable) in titles.
STOPWORDS = [
  'and',
  'approach',
  'approaches',
  'based',
  'experiment',
  'experiments',
  'exploration',
  'explorations',
  'for',
  'from',
  'into',
  'method',
  'methods',
  'new',
  'one',
  'onto',
  'per',
  'scale',
  'specific',
  'the',
  'using',
  'with',
]


def normalise_first_N_words_of_title(title, N):
  words = title.split()

  # First, normalise the hyphens (which should remove any non-hyphen punctuation
  # and reduce any sequences of multiple hyphens to a single hyphen).
  # Then remove any words shorter than 3 characters (a, in, of, ...) and any
  # stop-words.
  words = map(normalise_hyphens_strip_punctuation, words)
  words = [w for w in words if len(w) >= 3 and w not in STOPWORDS]

  rejoined_words = []
  for word in words:
    rejoined_words.extend(split_word_at_hyphens(word))
  # Remove any empty components (which would imply one or more non-hyphen dashes).
  words = filter(None, rejoined_words)

  # Only use the first N words.
  return "-".join(map(normalise_title_word, words[:N]))


UNINFORMATIVE_HYPHENATED_COMPONENTS = [
  "based",    # eg, "WordNet-based X" is no more informative than just "WordNet X"
  "scale",    # eg, "large-scale X" is hardly more informative than just "large X"
  "specific", # eg, "corpus-specific X" is hardly more informative than just "corpus X"
]


def split_word_at_hyphens(word):
  # Split at hyphens (filtering any empty components, which imply adjacent hyphens).
  # Then, if a component is shorter than 3 characters ("of", "in", ...), join it to the
  # preceding component (or the following component if there is no preceding component.
  comps = filter(None, word.split('-'))
  if not comps:
    return ""

  # Now we can assume that 'comps' contains at least one non-empty string.
  # Handle the possibility that the first component is shorter than 3 chars.
  if len(comps) >= 2 and len(comps[0]) < 3:
    comps[0:2] = [("%s-%s" % (comps[0], comps[1]))]

  # Now handle all components after the first.
  rejoined_comps = [comps[0]]
  for comp in comps[1:]:
    if comp in UNINFORMATIVE_HYPHENATED_COMPONENTS:
      continue
    if len(comp) < 3:
      rejoined_comps[-1] = "%s-%s" % (rejoined_comps[-1], comp)
    else:
      rejoined_comps.append(comp)

  return rejoined_comps


def normalise_hyphens_strip_punctuation(w):
  # We assume that word 'w' contains no whitespace.  It may contain hyphens,
  # which we should not remove (but we should reduce any sequences of multiple
  # hyphens to a single hyphen).

  # First, let's invoke 'transliterate_to_ascii', in case there are any
  # hyphen-like characters that we want to convert into real ASCII hyphens.
  # While we're at it, let's convert all the now-ASCII characters to lowercase.
  w = unicode_string_utils.transliterate_to_ascii(w).lower()

  # We want to retain any hyphens in the word.
  # Hence, split at the hyphens before we remove punctuation, so we can
  # re-join the pieces with hyphens later.  We remove any empty word pieces,
  # because these indicate that there were multiple adjacent hyphens in the word.
  # As an added benefit, this will also ensure that the re-assembled 'w' does not
  # begin or end with a hyphen.
  word_pieces = filter(None, w.split("-"))
  word_pieces = map(strip_punctuation_and_whitespace, word_pieces)
  return '-'.join(word_pieces)


def normalise_title_word(w):
  # We assume len(w) >= 3, and 'w' is lowercase with no non-hyphen punctuation.
  # 'w' may contain non-adjacent hyphens.

  # FIXME:  Extract the value 7 out into the 'constants' module.
  J = 7

  # Our simple heuristic for truncation is:
  #  1. If it is equal to or less than the allowable length, return it now.
  #  2. Else, truncate it at that length.
  #  3. If the truncated word ends in a hyphen, cut it off; go to step 3.
  #  4. Else, if the truncated word ends in a vowel that is preceded by a
  #     consonant or a hyphen (ie, a vowel that is not preceded by a vowel
  #     or the start of the string), cut it off; go to step 3.
  #  5. Else, if the second-last character of the truncated word is a hyphen
  #     (eg, "best-f" from "best-first"), cut off the hyphen and following
  #     character.
  #
  # Remember that we've already invoked 'transliterate_to_ascii' and 'lower',
  # so the only vowels left in the string should be lowercase ASCII vowels.

  if len(w) <= J:
    return w

  w = w[:J]
  while 1:
    if w[-1] == '-':
      w = w[:-1]
    elif (w[-1] in "aeiou") and w[:-1] and (w[-2] not in "aeiou"):
      w = w[:-1]
    else:
      return w


def test_author_name_normalisation():
  tests = [
    ("Kay", "kay"),
    ("Mr.E", "mre"),
    ("Wang", "wang"),
    ("Curran", "curran"),
    ("Fekete", "fekete"),
    ("Manning", "manning"),
    ("Nothman", "nothman"),
    ("O'Keefe", "okeefe"),
    ("Ringland", "ringlan"),
    ("Koprinska", "koprins"),
    ("Kummerfeld", "kummerf"),
    ("Balasuriya", "balasur"),
    (u"M\u00FCller", u'muller'),  # Contains a non-ASCII character
    ("Durrant-White", "durrant"),
  ]
  test_framework.test_and_compare(tests, normalise_lastname, "Author name")


def test_title_word_normalisation():
  tests = [
    ("word", "word"),
    ("tube", "tube"),
    ("light", "light"),
    ("sense", "sense"),
    ("domain", "domain"),
    ("jacobi", "jacobi"),
    ("chance", "chance"),
    ("12345", "12345"),
    ("12345-7", "12345-7"),
    ("123456", "123456"),
    ("123456-7", "123456"),
    ("scaling", "scaling"),
    ("strange", "strange"),
    ("semantic", "semant"),
    ("research", "researc"),
    ("citation", "citatio"),
    ("searching", "search"),
    ("retrieval", "retriev"),
    ("iostreams", "iostrea"),
    ("similarity", "similar"),
    ("co-occurrence", "co-occ"),
  ]
  test_framework.test_and_compare(tests, normalise_title_word, "Title word")


def test_normalise_first_N_words_of_title():
  def normalise_first_3_title_words(title):
    N = 3
    return normalise_first_N_words_of_title(title, N)

  tests = [
    ("Experiments in word domain disambiguation for parallel texts",
        "experim-word-domain"),
    ("The role of domain information in word sense disambiguation",
        "role-domain-inform"),
    ("Automatic retrieval and clustering of similar words",
        "automat-retriev-cluster"),
    ("A general framework for distributional similarity",
        "general-framew-distrib"),
    ("A maximum entropy part-of-speech tagger",
        "maximum-entropy-part-of"),
    ("Domain-specific sense distributions and predominant sense acquisition",
        "domain-sense-distrib"),
    ("Sussx: WSD using automatically acquired predominant senses",
        "sussx-wsd-automat"),
    ("Scaling context space",
        "scaling-context-space"),
    ("Co-occurrence Retrieval: A Flexible Framework for Lexical Distributional Similarity",
        "co-occ-retriev-flexibl"),
    ("Discovering corpus-specific word senses",
        "discov-corpus-word"),
    ("Using domain information for word sense disambiguation",
        "domain-inform-word"),
    ("Web-scale distributional similarity and entity set expansion",
        "web-distrib-similar"),
    ("From predicting predominant senses to local context for word sense disambiguation",
        "predict-predom-senses"),
    ("Large-Scale Syntactic Processing: Parsing the Web Final Report of the 2009 JHU CLSP Workshop",
        "large-syntact-process"),
    ("Robust, applied morphological generation",
        "robust-applied-morphol"),
    ("From distributional to semantic similarity",
        "distrib-semant-similar"),
    ("TnT: a statistical part-of-speech tagger",
        "tnt-statist-part-of"),
    ("A best-first probabilistic shift-reduce parser",
        "best-first-probab"),
    ("Using automatically acquired predominant senses for word sense disambiguation",
        "automat-acquir-predom"),
    ("Evaluating WordNet-based Measures of Lexical Semantic Relatedness",
        "evaluat-wordnet-measur"),
  ]
  test_framework.test_and_compare(tests, normalise_first_3_title_words, "First 3 title words")


def main():
  test_author_name_normalisation()
  test_title_word_normalisation()
  test_normalise_first_N_words_of_title()


if __name__ == "__main__":
  main()

