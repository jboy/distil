#!/usr/bin/env python
#
# filesystem_utils.py: Non-repository-aware filesystem-manipulation functions.
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
import shutil
import time

import test_framework


### Errors that may be thrown by this module.


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class EmptyFilename(Error):
  def __init__(self):
    pass

  def __str__(self):
    return "Empty filename encountered"


class NoFilenameSuffix(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return "No suffix found on filename '%s'" % self.fname


class FileNotFound(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return "File '%s' does not exist" % self.fname


class DirectoryNotFound(Error):
  def __init__(self, dirname):
    self.dirname = dirname

  def __str__(self):
    return "Directory '%s' does not exist" % self.dirname


### These are the public functions of the exported API.


def get_suffix(fname, allow_absent_suffix=False):
  """Extract and return the suffix of 'fname', *including* the period preceding the suffix."""

  # Beware of either empty string or None.
  if not fname:
    raise EmptyFilename()

  dotted_components = fname.split(".")
  if len(dotted_components) < 2:
    # No suffix -- what can we do here?
    if allow_absent_suffix:
      return ""
    else:
      raise NoFilenameSuffix(fname)

  # Need to handle suffixes of compressed files (eg, "gz", "bz2", "Z", etc.)
  # specially, since these often follow another suffix which we'll also want
  # to include (eg, "ps.gz").
  if dotted_components[-1].lower() in ["gz", "bz2", "z"]:
    if len(dotted_components) < 3:
      # No suffix before the compression suffix.
      if allow_absent_suffix:
        return dotted_components[-1]
      else:
        raise NoFilenameSuffix(fname)
    suffix = '.'.join(dotted_components[-2:])
  else:
    suffix = dotted_components[-1]

  return ('.' + suffix)


def move_and_rename(src_fname, dest_dir, dest_fname):
  """Move file 'src_fname' into 'dest_dir' with 'dest_fname'.

  This function is intended to be used to move+rename files before they've been
  committed into the repository.  Once the files have been committed, you should
  instead use the function 'repository.move'.
  """
  new_dir_and_fname = os.path.join(dest_dir, dest_fname)
  shutil.move(src_fname, new_dir_and_fname)

  return new_dir_and_fname


def write_config_file(list_of_sections, fname_abspath):
  """Write 'list_of_sections' to the file named by 'fname_abspath'.

  'list_of_sections' is a list of pairs, where the first element in each pair
  is the name of the section, and the second element is a list of variables
  defined in that section.
 
  Each "variable" in the list is itself a pair: the name of the variable and
  its value (both strings).
  """
  # OK, since the ConfigParser 'write' method seems to be unable to maintain
  # the ordering of the sections and variables (at least in Python 2.6), thus
  # making it absolutely f*cking useless, we'll do this ourselves.
  f = open(fname_abspath, 'w')
  for i, (section_name, variables) in enumerate(list_of_sections):
    f.write("[%s]\n" % section_name.strip())
    for var_name, var_value in variables:
      f.write("%s = %s\n" % (var_name.strip(), var_value.strip()))

    # Insert an empty line between sections (but not after the last section).
    if i < len(list_of_sections) - 1:
      f.write("\n")


### Anything below this point is not part of the exported API.


def add_datestamp(dest_dir):
  """Add a date/timestamp file ".date-added.txt" in the directory 'dest_dir'.

  Note that this is in a separate function, to ensure that the file is closed
  and flushed to disk before any other operations (like a Git commit) occur.
  """

  date_added = open(os.path.join(dest_dir, ".date-added.txt"), 'w')

  # Print the current time in seconds since the epoch (for easy parsing),
  # followed by the human-readable version.
  print >> date_added, get_datestamp_str()


def get_datestamp_str():
  """Return a string containing the current time in seconds since the epoch
  (for easy parsing), followed by the human-readable version.
  """
  return "%s %s" % get_datestamp()


def get_datestamp():
  """Return a tuple containing the current time in seconds since the epoch
  (for easy parsing), followed by the human-readable version.
  """
  return (int(time.time()), time.ctime())


def test_get_suffix():
  tests = [
    (None, None, EmptyFilename()),
    ("", None, EmptyFilename()),
    ("foo", None, NoFilenameSuffix("foo")),
    ("foo.gz", None, NoFilenameSuffix("foo.gz")),
    ("foo.ps.gz", ".ps.gz", None),
    ("foo.ps", ".ps", None),
    ("foo.pdf", ".pdf", None),
    ("foo.bar.pdf", ".pdf", None),
    ("foo.bar.pdf.Z", ".pdf.Z", None),
  ]
  test_framework.test_and_compare_and_catch(tests, get_suffix, "get_suffix")


def main():
  test_get_suffix()


if __name__ == "__main__":
  main()

