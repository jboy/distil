#!/usr/bin/env python
#
# stored_bibs.py: Manage all the files related to stored bib entries.
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
import errno

import bibfile_utils
import config
import constants
import filesystem_utils
import repository
import topic_tag_file_io


### Errors that may be thrown by this module.


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class MissingBibtexEntry(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return "BibTeX file '%s' does not contain any entries" % self.fname


class MultipleEntriesInFile(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return "BibTeX file '%s' contains multiple entries (not yet supported)" % \
        self.fname


class DirectoryAlreadyExistsInBibs(Error):
  def __init__(self, dirname):
    self.dirname = dirname

  def __str__(self):
    return "directory '%s' already exists in bibs" % self.dirname


### These are the public functions of the exported API.


def store_new_bib(bib_fname, doc_fname=None, abstract_fname=None):
  """Store a new bib-file in the doclib."""

  if not os.path.exists(bib_fname):
    raise filesystem_utils.FileNotFound(bib_fname)
  if doc_fname and not os.path.exists(doc_fname):
    raise filesystem_utils.FileNotFound(doc_fname)
  if abstract_fname and not os.path.exists(abstract_fname):
    raise filesystem_utils.FileNotFound(abstract_fname)

  # Store the bib-entry in a directory named after the cite-key.
  # This will ensure an almost-unique directory-name for each bib-entry, while
  # also enabling duplicate bib-entries to be detected.
  cite_key = get_one_cite_key(bib_fname)
  bibs_subdir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR)
  cite_key_dir_abspath = os.path.join(bibs_subdir_abspath, cite_key)
  try:
    os.makedirs(cite_key_dir_abspath)
  except OSError as e:
    if e.errno == errno.EEXIST:
      raise DirectoryAlreadyExistsInBibs(cite_key)
    else:
      raise

  new_bib_fname_abspath = \
      filesystem_utils.move_and_rename(bib_fname, cite_key_dir_abspath,
          cite_key + ".bib")
  bibfile_utils.replace_cite_key_in_file(cite_key, new_bib_fname_abspath)

  if doc_fname:
    filesystem_utils.move_and_rename(doc_fname, cite_key_dir_abspath,
        cite_key + filesystem_utils.get_suffix(doc_fname))
  if abstract_fname:
    filesystem_utils.move_and_rename(abstract_fname, cite_key_dir_abspath,
        constants.ABSTRACT_FNAME)

  filesystem_utils.add_datestamp(cite_key_dir_abspath)
  repository.add_and_commit_new_cite_key_dir(cite_key)

  # Do we want to merge the commit in the following function with the commit
  # in 'add_and_commit_new_cite_key_dir'?
  topic_tag_file_io.update_topic_tags_for_cite_key(cite_key, [], "new unread")

  return (cite_key, cite_key_dir_abspath)


def change_cite_key_and_rename_dir(curr_cite_key, new_cite_key):
  """Change 'curr_cite_key' to 'new_cite_key', and rename the cite-key directory
  and the files within it accordingly.
  
  Cite-keys are auto-generated to be predictable and consistent, so it's not
  recommended that you change them manually, but if you must, this function
  will enable you to do so.

  It's assumed that the cite-key directory, and the files within it, have been
  committed to the repository already.  (For example, perhaps you've just added
  a new bib+doc, and you notice that the auto-generated cite-key is terrible,
  and now you want to change it.)
  """

  # Rename the cite-key dir.
  # Rename the bib file and, if present, the doc.
  # Change the cite-key in the bib file.
  # Update the topic-tags indices appropriately.

  bibs_subdir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR)
  curr_cite_key_dir_abspath = os.path.join(bibs_subdir_abspath, curr_cite_key)
  new_cite_key_dir_abspath = os.path.join(bibs_subdir_abspath, new_cite_key)

  if not os.path.exists(curr_cite_key_dir_abspath):
    raise filesystem_utils.DirectoryNotFound(curr_cite_key_dir_abspath)
  if os.path.exists(new_cite_key_dir_abspath):
    raise DirectoryAlreadyExistsInBibs(new_cite_key)
  repository.move(curr_cite_key_dir_abspath, new_cite_key_dir_abspath)
  dirs_modified_abspaths = [curr_cite_key_dir_abspath, new_cite_key_dir_abspath]

  curr_bib_fname_abspath = os.path.join(new_cite_key_dir_abspath, curr_cite_key + ".bib")
  new_bib_fname_abspath = os.path.join(new_cite_key_dir_abspath, new_cite_key + ".bib")
  repository.move(curr_bib_fname_abspath, new_bib_fname_abspath)
  bibfile_utils.replace_cite_key_in_file(new_cite_key, new_bib_fname_abspath)

  doc_attrs = get_doc_attrs(new_cite_key, curr_cite_key)
  if doc_attrs:
    # There is a doc in this cite-key dir.
    curr_doc_fname_abspath = os.path.join(new_cite_key_dir_abspath, doc_attrs["doc-name"])
    new_doc_fname_abspath = os.path.join(new_cite_key_dir_abspath, new_cite_key + doc_attrs["doc-suffix"])
    repository.move(curr_doc_fname_abspath, new_doc_fname_abspath)

  topic_tags_fname_abspath = os.path.join(new_cite_key_dir_abspath, constants.TOPIC_TAGS_FNAME)
  if os.path.exists(topic_tags_fname_abspath):
    # There are topic tags, so we need to update the indices.
    topic_tags = topic_tag_file_io.read_topic_tags(topic_tags_fname_abspath)

    # Note that, because the current cite-key is already in this topic-tag index,
    # we know that this topic-tag index will exist, so we use 'add...to_existing'
    # rather than 'add..._to_new' for the new cite-key.
    index_dir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.TOPIC_TAG_INDEX_SUBDIR)
    topic_tag_file_io.add_cite_key_to_existing_topic_tag_index(new_cite_key, topic_tags, index_dir_abspath)
    topic_tag_file_io.remove_cite_key_from_topic_tag_index(curr_cite_key, topic_tags, index_dir_abspath)

    dirs_modified_abspaths.append(index_dir_abspath)

  repository.commit(dirs_modified_abspaths,
      "Renamed cite-key '%s' to '%s'" % (curr_cite_key, new_cite_key))


def get_doc_attrs(cite_key, doc_fname_startswith=None):
  """Return a dictionary of attributes (name, suffix, type) about the doc.

  This function is intended to be run only when doc is in the the cite-key
  directory already.

  If there is no doc in the cite-key directory, an empty dict will be returned.

  In general, you should not supply a value for 'doc_fname_startswith';
  when left to the default value of None, the value of 'cite_key' will be used,
  which will generally be the correct behaviour.  (The only time a value
  should be supplied is when the doc filename does *not* begin with 'cite_key',
  which should only be the case when invoked by 'change_cite_key_and_rename_dir',
  mid-way through the file-renaming process.)
  """

  if not doc_fname_startswith:
    doc_fname_startswith = cite_key

  doc_attrs = {}

  cite_key_dir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key)
  if not os.path.exists(cite_key_dir_abspath):
    raise filesystem_utils.DirectoryNotFound(cite_key_dir_abspath)

  bib_fname_abspath = os.path.join(cite_key_dir_abspath, cite_key + ".bib")
  multiple_bib_entries = bibfile_utils.read_entries_from_file(bib_fname_abspath, False)
  # FIXME:  Should check that length of 'multiple_bib_entries' is exactly 1.

  doc_attrs["title"] = multiple_bib_entries[0]["title"]
  doc_attrs["year-published"] = multiple_bib_entries[0]["year"]
  #doc_attrs["title"] = ""

  # We don't know what the filename of the document will be, only that it will
  # begin with the cite-key, and not end with ".bib".  Hence, we will traverse
  # the directory, looking for any files that match these criteria.
  # FIXME:  This seems inefficient.  Would it be better to store the suffix in
  # a per-cite-key-dir ".meta" file instead?  Is it faster to parse a simple
  # config file or traverse a directory each time?
  matched_doc_fname = [fname
      for fname in os.listdir(cite_key_dir_abspath)
      if fname.startswith(doc_fname_startswith) and fname[-4:] != ".bib"]
  if matched_doc_fname:
    doc_fname = matched_doc_fname[0]
    doc_attrs["doc-name"] = doc_fname

    suffix = filesystem_utils.get_suffix(doc_fname)
    doc_attrs["doc-suffix"] = suffix
    doc_attrs["doc-type"] = suffix[1:].upper()

  date_added = open(os.path.join(cite_key_dir_abspath, ".date-added.txt")).read().split()[0]
  doc_attrs["date-added"] = date_added

  return doc_attrs


### Anything below this point is not part of the exported API.


def get_one_cite_key(bib_fname):
  keys_and_citations = \
      bibfile_utils.suggest_cite_keys_for_entries_in_file(bib_fname)

  if len(keys_and_citations) == 0:
    raise MissingBibtexEntry(bib_fname)
  if len(keys_and_citations) > 1:
    raise MultipleEntriesInFile(bib_fname)

  # [0] to get the only item in the list (a tuple), then [0] again to get the
  # first element in the tuple (the cite-key) -- the second element being a
  # dictionary of BibTeX entries.
  return keys_and_citations[0][0]

