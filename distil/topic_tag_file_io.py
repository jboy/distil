# topic_tag_file_io.py: File I/O for topic tags.
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


import itertools
import os
import shutil
import string
from collections import defaultdict

import config
import constants
import repository
import unicode_string_utils


def regenerate_topic_tag_index():
  """Regenerate the topic tag index, if it somehow gets messed up.
  
  This function is not called by any other Distil code; it's purely
  for administrator convenience.  You'll also need to commit the changes
  to the repository manually after invoking this function.
  """

  # First, nuke the existing index, if there is any of it left.
  index_dir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.TOPIC_TAG_INDEX_SUBDIR)
  if os.path.exists(index_dir_abspath):
    shutil.rmtree(index_dir_abspath)

  # Then re-create it.
  os.makedirs(index_dir_abspath)

  # Now traverse all the cite-key subdirectories, and collect any topic tags we find.
  bibs_subdir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR)
  all_cite_keys = os.listdir(bibs_subdir_abspath)
  topic_tag_index = collect_topic_tags(bibs_subdir_abspath, all_cite_keys)

  for topic_tag, cite_keys in topic_tag_index.items():
    topic_tag_index_abspath = os.path.join(index_dir_abspath, topic_tag)
    write_topic_tag_index(topic_tag_index_abspath, cite_keys, update_repository=False)


def collect_topic_tags(bibs_subdir_abspath, cite_keys):
  """Collect topic tags from all the 'cite_keys' specified.

  Returns a defaultdict instance that maps topic tags to the cite-keys tagged
  with the topic tags.
  """
  topic_tag_index = defaultdict(list)

  for cite_key in cite_keys:
    topic_tags_fname_abspath = \
        os.path.join(bibs_subdir_abspath, cite_key, constants.TOPIC_TAGS_FNAME)
    if os.path.exists(topic_tags_fname_abspath):
      tags = read_topic_tags(topic_tags_fname_abspath)
      for t in tags:
        topic_tag_index[t].append(cite_key)

  return topic_tag_index


# See http://en.wikipedia.org/wiki/Percent-encoding#Types_of_URI_characters
# and http://tools.ietf.org/html/rfc3986#section-2.2
# In theory, colons are also a problem, but I intend to handle them specially later
# as namespaces... somehow (perhaps converting "foo:bar" to "foo/bar", for example).
# For now, I just have to make sure I URL-encode them.
ALLOWED_PUNCTUATION = "-_.:"
STRIP_PUNCTUATION_AND_WHITESPACE = \
    unicode_string_utils.StripPunctuationAndWhitespace(ALLOWED_PUNCTUATION)

def sanitize_tag(s):
  return STRIP_PUNCTUATION_AND_WHITESPACE(unicode(s).lower())


def split_at_whitespace_and_commas(s):
  return s.replace(',', ' ').split()


def ensure_new_tags_are_actually_new(new_tags, chosen_tags):
  """If there are any "new tags" that are actually already-known tags,
  move them into "chosen tags".

  Note that 'new_tags' and 'chosen_tags' are both assumed to be sets.

  Note also that this modifies 'new_tags' and 'chosen_tags' in-place.
  """

  all_topic_tags = set(get_all_topic_tags(sort_tags=False))
  tags_to_move_to_chosen_tags = set([])
  for new_tag in new_tags:
    if new_tag in all_topic_tags:
      tags_to_move_to_chosen_tags.add(new_tag)

  chosen_tags |= tags_to_move_to_chosen_tags
  new_tags -= tags_to_move_to_chosen_tags


def update_topic_tags_for_cite_key(cite_key, chosen_tags, new_tags_str):
  """Update the topic tags for 'cite_key' to 'chosen_tags' (a collection of existing tags)
  and 'new_tags_str' (a string of whitespace-or-comma-delimited non-pre-existing tags).

  This function will sanitise all the tags.

  It will also ensure that all the "new tags" are actually new, moving them into the
  collection of "chosen tags" if they're not.
  """

  chosen_tags = set(map(sanitize_tag, chosen_tags))
  new_tags = set(map(sanitize_tag, split_at_whitespace_and_commas(new_tags_str)))
  ensure_new_tags_are_actually_new(new_tags, chosen_tags)

  prev_tags = set(get_topic_tags_for_cite_key(cite_key, sort_tags=False))
  if (chosen_tags == prev_tags) and not new_tags:
    # There were no changes to the tags for this cite-key.
    return

  added_tags = chosen_tags - prev_tags
  removed_tags = prev_tags - chosen_tags

  topic_tags_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key, constants.TOPIC_TAGS_FNAME)
  write_topic_tags(topic_tags_fname_abspath, list(chosen_tags) + list(new_tags))

  index_dir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.TOPIC_TAG_INDEX_SUBDIR)
  # Ensure that the index-dir actually exists.
  if not os.path.exists(index_dir_abspath):
    os.makedirs(index_dir_abspath)

  remove_cite_key_from_topic_tag_index(cite_key, removed_tags, index_dir_abspath)
  add_cite_key_to_existing_topic_tag_index(cite_key, added_tags, index_dir_abspath)
  add_cite_key_to_new_topic_tag_index(cite_key, new_tags, index_dir_abspath)

  # If this function was called, then something must have been changed...
  # so commit something.
  repository.commit([topic_tags_fname_abspath, index_dir_abspath],
      "updated topic tags for cite-key %s" % cite_key)


def remove_cite_key_from_topic_tag_index(cite_key, topic_tags, index_dir_abspath):
  """Remove 'cite_key' from the index for each topic tag.

  It is assumed that 'index_dir_abspath' exists and contains an index for each topic.
  """
  for topic_tag in topic_tags:
    topic_tag_index_abspath = os.path.join(index_dir_abspath, topic_tag)
    cite_keys = read_topic_tag_index(topic_tag_index_abspath)
    try:
      cite_keys.remove(cite_key)
    except ValueError as e:
      # Due to some malfunction, 'cite_key' wasn't in the list.
      # Perhaps something failed last time around?
      # Regardless, there's nothing we can do about it, and it won't
      # violate our postcondition (cite_key not in cite_keys) anyway.
      pass

    write_topic_tag_index(topic_tag_index_abspath, cite_keys)


def add_cite_key_to_existing_topic_tag_index(cite_key, topic_tags, index_dir_abspath):
  """Add 'cite_key' to the index for each topic tag.

  It is assumed that 'index_dir_abspath' exists and contains an index for each topic.
  """
  for topic_tag in topic_tags:
    topic_tag_index_abspath = os.path.join(index_dir_abspath, topic_tag)
    cite_keys = read_topic_tag_index(topic_tag_index_abspath)
    # We would assume that 'cite_key' would not be in 'cite_keys',
    # but just to be on the safe side, we'll perform this check first,
    # to ensure that 'cite_key' ends up in 'cite_keys' at most once.
    if cite_key not in cite_keys:
      cite_keys.append(cite_key)
    write_topic_tag_index(topic_tag_index_abspath, cite_keys)


def add_cite_key_to_new_topic_tag_index(cite_key, topic_tags, index_dir_abspath):
  """Add 'cite_key' to the newly-created index for each topic tag.

  It is assumed that 'index_dir_abspath' exists but does not contain an index for any of
  these topics.
  """
  for topic_tag in topic_tags:
    topic_tag_index_abspath = os.path.join(index_dir_abspath, topic_tag)
    write_topic_tag_index(topic_tag_index_abspath, [cite_key])


def write_topic_tag_index(fname_abspath, cite_keys, update_repository=True):
  """Write the list of cite-keys 'cite_keys' into the new topic tag index file
  'fname_abspath'.

  The list of cite-keys doesn't need to be sorted in advance, as it will be
  sorted in this function.
  """
  cite_keys.sort()

  # Does the file already exist?  This will determine whether we need to add it
  # to the repository before we can commit it.
  file_exists_before_write = os.path.exists(fname_abspath)

  # If there are no cite-keys, we want to delete the file from the directory
  # (since the file's presence will result in the presentation to the user
  # of an unused topic tag).
  if not cite_keys:
    # Delete the file, if it exists.
    if file_exists_before_write and update_repository:
      repository.remove(fname_abspath)
  else:
    open_file_write_one_per_line(fname_abspath, cite_keys)
    if not file_exists_before_write and update_repository:
      repository.add(fname_abspath)


def read_topic_tag_index(fname):
  """Return a list of the cite-keys found in file 'fname'.

  Assumes the file exists, or else an exception will be raised.
  """
  s = open(fname).read()
  return s.split()


def get_all_topic_tags(sort_tags=True):
  """Return a list of all the topic tags in the topic tag index."""

  index_dir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.TOPIC_TAG_INDEX_SUBDIR)
  all_topic_tags = os.listdir(index_dir_abspath)
  if sort_tags:
    all_topic_tags.sort()
  return all_topic_tags


def get_topic_tags_for_cite_key(cite_key, sort_tags=True):
  """Get the topic tags which tag 'cite_key'."""
  topic_tags_fname_abspath = \
      os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key, constants.TOPIC_TAGS_FNAME)

  if os.path.exists(topic_tags_fname_abspath):
    topic_tags = read_topic_tags(topic_tags_fname_abspath)
    if sort_tags:
      topic_tags.sort()
    return topic_tags
  else:
    return []


def write_topic_tags(fname_abspath, topic_tags):
  """Write the list of topic tags 'topic_tags' into the new topic tags file
  'fname_abspath'.

  The list of topic tags doesn't need to be sorted in advance, as it will be
  sorted in this function.
  """
  topic_tags.sort()

  # Does the file already exist?  This will determine whether we need to add it
  # to the repository before we can commit it.
  file_exists_before_write = os.path.exists(fname_abspath)

  # If there are no topic tags, we want to write an empty file rather than a
  # file containing only a newline.
  if not topic_tags:
    empty_file_contents(fname_abspath)
  else:
    open_file_write_one_per_line(fname_abspath, topic_tags)

  if not file_exists_before_write:
    repository.add(fname_abspath)


def open_file_write_one_per_line(fname, items):
  """A convenience function to ensure a file is closed and flushed to disk
  before any other operations (like a Git add) occur.
  """
  f = open(fname, 'w')
  for i in items:
    print >> f, i


def empty_file_contents(fname):
  """A convenience function to ensure a file is closed and flushed to disk
  before any other operations (like a Git add) occur.
  """
  f = open(fname, 'w')
  f.truncate()


def read_topic_tags(fname):
  """Return a list of the tags found in file 'fname'.

  Assumes the file exists, or else an exception will be raised.
  """
  s = open(fname).read()
  return s.split()

