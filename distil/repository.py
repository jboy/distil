# repository.py: Wrapper functions for repository access.
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
import subprocess

import config
import constants


def add_and_commit_new_cite_key_dir(cite_key):
  bibs_subdir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR)
  commit_message = "Distil created bib-entry %s." % cite_key
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "add", cite_key],
      cwd=bibs_subdir_abspath)
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "commit", "-m", commit_message, cite_key],
      cwd=bibs_subdir_abspath)


def add_and_commit_new_attachment_dir(fname, dirname):
  attachments_subdir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.ATTACHMENTS_SUBDIR)
  commit_message = 'Distil stored file attachment "%s" in new directory %s.' % (fname, dirname)
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "add", dirname],
      cwd=attachments_subdir_abspath)
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "commit", "-m", commit_message, dirname],
      cwd=attachments_subdir_abspath)


def add(fname_abspath):
  """A generic repository "add" function."""
  rel_fname = path_rel_doclib_base(fname_abspath)
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "add", rel_fname],
      cwd=config.DOCLIB_BASE_ABSPATH)


def remove(fname_abspath):
  """A generic repository "remove" function."""
  rel_fname = path_rel_doclib_base(fname_abspath)
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "rm", rel_fname],
      cwd=config.DOCLIB_BASE_ABSPATH)


def move(src_fname_abspath, dest_fname_abspath):
  """A generic repository "move" function."""
  rel_src_fname = path_rel_doclib_base(src_fname_abspath)
  rel_dest_fname = path_rel_doclib_base(dest_fname_abspath)
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "mv", rel_src_fname, rel_dest_fname],
      cwd=config.DOCLIB_BASE_ABSPATH)


def commit(fname_abspaths, reason):
  """A generic repository "commit" function.
  
  'fname_abspaths' is a list of filename absolute-paths;
  'reason' is a reason for the commit.
  """
  relative_fnames = map(path_rel_doclib_base, fname_abspaths)
  commit_message = "Distil operation: %s" % reason
  subprocess.check_call(
      [config.GIT_EXECUTABLE, "commit", "-m", commit_message] + relative_fnames,
      cwd=config.DOCLIB_BASE_ABSPATH)


def path_rel_doclib_base(fname_abspath):
  """Return the path of 'fname_abspath' relative to the doclib base."""
  return os.path.relpath(os.path.normpath(fname_abspath), config.DOCLIB_BASE_ABSPATH)

