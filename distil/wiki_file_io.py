# wiki_file_io.py: File I/O for wiki text.
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


import os
import time

import config
import constants
import repository


def update_notes_for_cite_key(cite_key, notes, change_descr):
  notes_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key, constants.NOTES_FNAME)
  change_descrs_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key, constants.NOTES_CHANGE_DESCRS_FNAME)

  update_wiki_text(notes, notes_fname_abspath, change_descr, change_descrs_fname_abspath, "cite-key %s" % cite_key)


def update_text_for_wiki_page(wiki_word, text, change_descr):
  wiki_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.WIKI_SUBDIR, wiki_word, wiki_word + constants.WIKI_FNAME_SUFFIX)
  change_descrs_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.WIKI_SUBDIR, wiki_word, constants.WIKI_TEXT_CHANGE_DESCRS_FNAME)

  update_wiki_text(text, wiki_fname_abspath, change_descr, change_descrs_fname_abspath, "wiki page '%s'" % wiki_word)


def update_wiki_text(wiki_text, wiki_text_fname_abspath, change_descr, change_descrs_fname_abspath, what_was_changed):
  ensure_file_added_to_repo_if_created(open_file_write_string,
      wiki_text_fname_abspath, wiki_text)

  # If this function was called, then the wiki-text was changed, which means
  # that we should also append *something* to the notes-change descriptions
  # (even if it's just a datestamp and an empty-string).

  # We'll print the current time in seconds since the epoch (for easy parsing),
  # followed by the human-readable version.
  datestamp = "%s %s" % (int(time.time()), time.ctime())

  # Convert every whitespace sequence in 'change_descr' to a single space character,
  # to ensure there are not somehow newlines written to the file (which would mess up
  # our assumption that odd lines are datestamps and even lines are descriptions).
  change_descr = " ".join(change_descr.split())

  ensure_file_added_to_repo_if_created(open_file_append_strings,
      change_descrs_fname_abspath, [datestamp, change_descr])

  repository.commit([wiki_text_fname_abspath, change_descrs_fname_abspath],
      "updated notes for %s: %s" % (what_was_changed, change_descr))


def get_notes_for_cite_key(cite_key):
  notes_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key, constants.NOTES_FNAME)
  return get_wiki_text(notes_fname_abspath)


def get_text_for_wiki_page(wiki_word):
  wiki_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.WIKI_SUBDIR, wiki_word, wiki_word + constants.WIKI_FNAME_SUFFIX)
  return get_wiki_text(wiki_fname_abspath)


def get_wiki_text(wiki_text_fname_abspath):
  if os.path.exists(wiki_text_fname_abspath):
    return open(wiki_text_fname_abspath).read().rstrip().replace('\r\n', '\n').replace('\r', '\n')
  else:
    return ""


def ensure_file_added_to_repo_if_created(file_writing_func, fname_abspath, arg_to_write):
  """Does the file 'fname_abspath' already exist?
  
  If it doesn't already exist, then it will be created by 'file_writing_func',
  which means it will be a new file, not yet added into the repository.

  This function will ensure the file is added to the repository if the file is
  created by the file-writing function.
  """

  file_exists_before_write = os.path.exists(fname_abspath)
  file_writing_func(fname_abspath, arg_to_write)
  if not file_exists_before_write:
    # The file was just created.
    repository.add(fname_abspath)


def open_file_write_string(fname, s):
  """A convenience function to ensure a file is closed and flushed to disk
  before any other operations (like a Git add) occur.
  """
  f = open(fname, 'w')
  print >> f, s.encode("utf8")


def open_file_append_strings(fname, strings):
  """A convenience function to ensure a file is closed and flushed to disk
  before any other operations (like a Git add) occur.
  """
  f = open(fname, 'a')
  for s in strings:
    print >> f, s.encode("utf8")

