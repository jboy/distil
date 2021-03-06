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
import glob
import os
import shutil
import urllib2
import uuid

import config
import constants
import filesystem_utils
import repository
import unicode_string_utils


### These are the public functions of the exported API.


ATTACHMENT_IMPORT_SEARCH_LOCATIONS = [
    "~/Downloads",
    "~/Desktop",
    "~"
]


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class InvalidFilename(Error):
  def __init__(self, fname):
    self.fname = fname
  
  def __str__(self):
    return "'%s' is an invalid filename" % self.fname


class InvalidDirname(Error):
  def __init__(self, dirname):
    self.dirname = dirname
  
  def __str__(self):
    return "'%s' is an invalid directory name" % self.dirname


class CannotOpenURL(Error):
  def __init__(self, url, http_error_code):
    self.url = url
    self.http_error_code = http_error_code
  
  def __str__(self):
    return "Cannot open the URL '%s' (HTTP error %s)" % (self.url, self.http_error_code)


class FileNotFoundInDirectory(Error):
  def __init__(self, fname, dirname):
    self.fname = fname
    self.dirname = dirname
  
  def __str__(self):
    return "Cannot find the file '%s' in the specified directory '%s'" % (self.fname, self.dirname)


class FileNotFoundInDirectorySearch(Error):
  def __init__(self, fname, dirname_list):
    self.fname = fname
    self.dirname_list = dirname_list
  
  def __str__(self):
    return "Cannot find the file '%s' in any of the directories [%s]" \
        % (self.fname, ", ".join(self.dirname_list))


STRIP_ALL_PUNCTUATION_AND_WHITESPACE = \
    unicode_string_utils.StripPunctuationAndWhitespace()

ALLOWED_PUNCTUATION = "-_.:"
STRIP_MOST_PUNCTUATION_AND_WHITESPACE = \
    unicode_string_utils.StripPunctuationAndWhitespace(ALLOWED_PUNCTUATION)

# Don't change these parameter names, because we use double-asterisk
# function invocation to pass parameters by name.
def store_new_attachment_incl_dirpath(filename, dirpath="", new_filename="", short_descr="", source_url=""):

  # Ensure the filename isn't empty, or just dots or some other punctuation.
  if STRIP_ALL_PUNCTUATION_AND_WHITESPACE(unicode(filename)) == "":
    raise InvalidFilename(filename)

  if filename.startswith("http://"):
    # Be ready to handle 404s, etc.
    try:
      # Assume it's a URL to fetch.
      url_contents = urllib2.urlopen(filename, 'rb')
      (attachment_id, attachment_path) = \
          store_new_attachment(filename, short_descr, source_url, new_filename, url_contents)
      return attachment_id
    except urllib2.HTTPError as e:
      raise CannotOpenURL(filename, e.code)
  elif dirpath:
    # Ensure the dirname isn't empty, or just dots or some other punctuation.
    if STRIP_ALL_PUNCTUATION_AND_WHITESPACE(unicode(dirpath)) == "":
      raise InvalidDirname(dirpath)

    filename_incl_dirpath = os.path.join(dirpath, filename)
    glob_match = glob.glob(filename_incl_dirpath)
    if glob_match:
      for m in glob_match:
        (attachment_id, attachment_path) = \
            store_new_attachment(m, short_descr, source_url, new_filename)
      return attachment_id
    else:
      raise FileNotFoundInDirectory(filename, dirpath)
  else:
    for loc in ATTACHMENT_IMPORT_SEARCH_LOCATIONS:
      location = os.path.expanduser(loc)

      filename_incl_dirpath = os.path.join(location, filename)
      glob_match = glob.glob(filename_incl_dirpath)
      if glob_match:
        for m in glob_match:
          (attachment_id, attachment_path) = \
              store_new_attachment(m, short_descr, source_url, new_filename)
        return attachment_id

    # Otherwise, no luck finding the named file in any of the search directories.
    raise FileNotFoundInDirectorySearch(filename, ATTACHMENT_IMPORT_SEARCH_LOCATIONS)


def store_new_attachment(attachment_fname, short_descr="", source_url="", new_fname="",
    url_contents=None):
  """Store a new attachment in the doclib."""

  if url_contents:
    # The user specified a URL rather than the name of a file on disk.
    # 'url_contents' is a file-like object that contains the contents of the URL.
    # Hence, don't test whether the 'attachment_fname' file exists on disk.
    pass
  elif not os.path.exists(attachment_fname):
    raise filesystem_utils.FileNotFound(attachment_fname)

  if new_fname:
    # We'll use this as the filename instead.
    target_fname = STRIP_MOST_PUNCTUATION_AND_WHITESPACE(unicode(
        new_fname.replace(' ', '-').replace('/', '-')))
  else:
    # I've checked that 'os.path.basename' also does the correct thing for URLs.
    target_fname = os.path.basename(attachment_fname)

  # Ensure the filename doesn't begin with a dot (which we reserve for
  # book-keeping files like ".metadata").
  target_fname = target_fname.lstrip('.')
  if target_fname == "":
    raise filesystem_utils.EmptyFilename()

  # Since different attachments may very well have duplicate filenames,
  # we store each attachment in a subdirectory with a "unique" dirname.
  (dirname, dirname_abspath) = create_unique_dirname(target_fname)

  if url_contents:
    # Save the URL contents into an appropriately-named file.
    target_fname_abspath = os.path.join(dirname_abspath, target_fname)
    target_f = open(target_fname_abspath, 'wb')
    shutil.copyfileobj(url_contents, target_f)
  else:
    # We want to move a file on disk.
    new_attachment_fname_abspath = \
        filesystem_utils.move_and_rename(attachment_fname, dirname_abspath,
            target_fname)

  config_sections = [
    ("Description", [
      ("short-descr", short_descr),
      ("source-url", source_url),
    ]),
    ("Cache", [
      ("filename", target_fname),
      ("suffix", filesystem_utils.get_suffix(target_fname)),
    ]),
    ("Creation", [
      ("date-added", filesystem_utils.get_datestamp_str()),
    ]),
  ]

  filesystem_utils.write_config_file(config_sections, os.path.join(dirname_abspath, ".metadata"))
  repository.add_and_commit_new_attachment_dir(target_fname, dirname)

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

