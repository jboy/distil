#!/usr/bin/env python
#
# attachments.py: Manage all the files related to file attachments.
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


import base64
import ConfigParser
import errno
import os
import uuid

import config
import constants
import filesystem_utils
import repository


### These are the public functions of the exported API.


def store_new_attachment(attachment_fname, short_descr="", source_url=""):
  """Store a new attachment in the doclib."""

  if not os.path.exists(attachment_fname):
    raise filesystem_utils.FileNotFound(attachment_fname)
  attachment_basename = os.path.basename(attachment_fname)

  # Since different attachments may very well have duplicate filenames,
  # we store each attachment in a subdirectory with a "unique" dirname.
  (dirname, dirname_abspath) = create_unique_dirname(attachment_basename)

  new_attachment_fname_abspath = \
      filesystem_utils.move_and_rename(attachment_fname, dirname_abspath,
          attachment_basename)

  config_sections = [
    ("Description", [
      ("short-descr", short_descr),
      ("source-url", source_url),
    ]),
    ("Cache", [
      ("filename", attachment_basename),
      ("suffix", filesystem_utils.get_suffix(attachment_basename)),
    ]),
    ("Creation", [
      ("date-added", filesystem_utils.get_datestamp_str()),
    ]),
  ]

  filesystem_utils.write_config_file(config_sections, os.path.join(dirname_abspath, ".metadata"))
  repository.add_and_commit_new_attachment_dir(attachment_basename, dirname)

  return (dirname, dirname_abspath)


def get_attachment_attrs(dirname):
    dirname_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.ATTACHMENTS_SUBDIR, dirname)

    metadata_abspath = os.path.join(dirname_abspath, ".metadata")
    cp = ConfigParser.SafeConfigParser()
    cp.read(metadata_abspath)
    fname = cp.get("Cache", "filename")
    fsize = get_human_readable_file_size(os.path.join(dirname_abspath, fname))
    descr = cp.get("Description", "short-descr")
    source_url = cp.get("Description", "source-url")
    suffix = cp.get("Cache", "suffix")
    ftype = suffix[1:].upper()
    static_path = "/static/%s/attachments/%s/%s" % (config.DOCLIB_SYMLINK_NAME, dirname, fname)

    return (fname, dirname, fsize, descr, source_url, suffix, ftype, static_path)


### Anything below this point is not part of the exported API.


def get_human_readable_file_size(fname_abspath):
  fsize = os.stat(fname_abspath).st_size
  for suffix in ['bytes', 'kB', 'MB', 'GB', 'TB']:
    if fsize < 1024.0:
      return "%3.1f %s" % (fsize, suffix)
    fsize /= 1024.0


def create_unique_dirname(fname):
  """Create a unique directory name (containing no punctuation or whitespace
  other than hyphens and underscores) from the given filename 'fname'.
  """
  # We'll generate a "unique" dirname and check whether it's already present;
  # if so, we'll keep trying until we generate a dirname which is NOT already
  # present.  (Note that this doesn't preclude the possibility that duplicate
  # "unique" dirnames could be generated simultaneously on different systems,
  # which would then clash when one system's repo is merged with the other,
  # but it's a pretty decent start.)

  dirname = generate_unique_dirname(fname)
  dirname_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.ATTACHMENTS_SUBDIR, dirname)

  while 1:
    try:
      os.makedirs(dirname_abspath)
    except OSError as e:
      if e.errno != errno.EEXIST:
        # The problem is *NOT* that a directory of this name already exists.
        # Hence, we'll propagate it.
        raise

      # Otherwise, a directory of this name already exists.
      # This will presumably occur about once every bazillion years or so...
      # So, we'll let ourselves loop again.
    else:
      return (dirname, dirname_abspath)


def generate_unique_dirname(fname):
  """Generate a unique directory name (containing no punctuation or whitespace
  other than hyphens and underscores) from the given filename 'fname'.
  """
  # Meh, hyphens and underscores look crap, so let's scrap them anyway.
  # Let's also truncate it to (at most) 12 characters, so it's not too long.
  return generate_unique_string_22().replace("-", "").replace("_", "")[:12]


def generate_unique_string_26():
  """Generate a unique string consisting only of digits and lowercase letters.

  The strings generated by this function are 26 characters in length.
  Each string is the base-32-encoded representation of the 16 bytes of a UUID.
  """
  return base64.b32encode(uuid.uuid4().bytes).lower().rstrip('=')


def generate_unique_string_22():
  """Generate a unique string consisting only of digits, letters, hyphens and
  underscores.

  The strings generated by this function are 22 characters in length.
  Each string is the "url-safe" base-64-encoded representation of the 16 bytes
  of a UUID.
  """
  return base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip('=')

