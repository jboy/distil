#!/usr/bin/env python
#
# bibgrep.py: Keyword searching in (un-indexed) bib-files.
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


import cProfile
import string
import types

import bibfile_utils
import config
import constants
import unicode_string_utils


### Errors that may be thrown by this module.


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


### These are the public functions of the exported API.


def grep_in_fname(expr, fname):
  query = build_query(expr)
  searchable_entries = extract_searchable_entry_text_from_file(fname)
  for cite_key, lines in searchable_entries:
    foo(query, cite_key, lines)


def foo(query, cite_key, lines):
  for q in query:
    if not any((line for line in lines if line.startswith(q))):
      return
  print cite_key


def build_query(expr):
  tokens = expr.replace(":", " ").split()
  return [unicode_string_utils.transliterate_to_ascii(t).lower() for t in tokens]


def extract_searchable_entry_text_from_file(fname):
  entries = bibfile_utils.read_entries_from_file(fname, False)
  return [extract_searchable_text(e) for e in entries]


def extract_searchable_text(entry):
  cite_key = entry["pid"]

  # Include the cite-key in the text that can be searched.
  text_lines = [cite_key]
  for field, funcs in FIELDS_TO_GREP:
    if entry.has_key(field):
      value = entry[field]

      # Apply field-specific processing functions.
      for func in funcs:
        if type(value) == types.ListType:
          result_values = []
          for v in value:
            res = func(v)
            if type(res) == types.ListType:
              result_values.extend(res)
            else:
              result_values.append(res)
          value = result_values
        else:
          value = func(value)

      # Transliterate to ASCII and convert to lowercase.
      if type(value) == types.ListType:
        value = [unicode_string_utils.transliterate_to_ascii(v).lower() for v in value]
      else:
        value = unicode_string_utils.transliterate_to_ascii(value).lower()

      # Add to the searchable text lines for this entry.
      if type(value) == types.ListType:
        # Remove duplicates.
        value = list(set(value))
        text_lines.extend(value)
      else:
        text_lines.append(value)

  return (cite_key, text_lines)


### Anything below this point is not part of the exported API.

def extract_author_lastname(author):
  return author["lastname"]


# We want "COLING/ACL" to be matched by the queries "COL", "COLING", "ACL", "COLING/ACL"
#  and "COLING-ACL".
# We want "(ICCASM)" to be matched by the queries "ICC" and "ICCASM".
# We want "on-line" and "online" to both be matched by the queries "on-line" and "online".
# We want "co-occurrence" and "cooccurrence" to both be matched by the queries
#  "co-occurrence" and "cooccurrence".
# We want "ACL-2000" to be matched by the queries "ACL", "2000" and "ACL-2000".
# We want "part-of-speech" and "part of speech" to both be matched by the queries
#  "part", "part of speech", "part-of-speech", "part-of" and "speech".
# We want "word-sense" and "word sense" to both be matched by the queries"
#  "word-sense" and "word sense".
#
# We also need to remove any backslashes and left or right braces, since these
# indicate non-ASCII Latex characters (which we want transliterated to ASCII).
#
# Hence, we will split all sentences at whitespace.
# Then, we will step through the list of tokens; for each token:
#   If it contains a slash, also insert the version with the slash converted
#   into a hyphen.
#   If it contains a hyphen, also insert the version with the hyphen stripped
#   and the version with the hyphen split into words.
#   Strip any punctuation at the beginning of words.

def split_at_ws_and_punct(s):
  final_tokens = []

  tokens_split_at_ws = s.split()
  for t in tokens_split_at_ws:

    # Remove any punctuation at the beginning of a token.
    while t and t[0] in string.punctuation:
      t = t.lstrip(t[0])
    if not t:
      continue

    # FIXME:  Still need to remove backslashes and left/right braces.
      
    final_tokens.append(t)

    # Note that the following two if-statements won't catch all weird and wonderful
    # permutations of slash-hyphen combinations...

    if '/' in t:
      tokens_split_at_slash = t.split('/')
      final_tokens.append('-'.join(tokens_split_at_slash))
      final_tokens.append("".join(tokens_split_at_slash))
      final_tokens.extend(tokens_split_at_slash)

    if '-' in t:
      tokens_split_at_hyphen = t.split('-')
      final_tokens.append("".join(tokens_split_at_hyphen))
      final_tokens.extend(tokens_split_at_hyphen)

  return final_tokens


def insert_ws_after_punct(s):
  replacements = [
    (',', ', '),
    (':', ': '),
    (';', '; '),
  ]
  for str, replace in replacements:
    s = s.replace(str, replace)

  return s



FIELDS_TO_GREP = [
  ("authors",    [extract_author_lastname]),
  ("booktitle",  [split_at_ws_and_punct]),
  ("journal",    [split_at_ws_and_punct]),
  ("keywords",   [insert_ws_after_punct, split_at_ws_and_punct]),
  ("location",   [split_at_ws_and_punct]),
  ("publisher",  [split_at_ws_and_punct]),
  ("series",     [split_at_ws_and_punct]),
  ("title",      [split_at_ws_and_punct]),
  ("year",       []),
]


def test_grep():
  grep_in_fname('ringland 2009 german',
      "/home/jboy/Study/MIT/2011/Schwa_Lab_Git_Repos/pubs/pubs.bib")


def main():
  cProfile.run('test_grep()', 'bibgrep_profile')


if __name__ == "__main__":
  main()

