# config.py: Read configuration files and provide a single point of access to variables.
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


import ConfigParser
import base64
import os
import re
import uuid


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class MissingDistilConfigFile(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return 'cannot find configuration file "%s".' % self.fname


class CannotOpenFile(Error):
  def __init__(self, fname):
    self.fname = fname

  def __str__(self):
    return 'cannot open file "%s" for reading.' % self.fname


# The name of a config file that is expected to exist in one of the directories
# listed in '_CONFIG_PATHS_TO_TRY'.
# (There is an example of this config file provided as "example.distil.cfg".)
_CONFIG_FNAME = ".distil.cfg"

# The paths in which to look for the config file '_CONFIG_FNAME'.
# (Add more directories to this list if you desire.)
_CONFIG_PATHS_TO_TRY = [
  os.getcwd(),  # The current directory
  os.path.expanduser("~"),  # The user's home directory
]

# The list of config files that the parser ultimately reads successfully, to
# enable later code to report this information if desired.
# (This list will be populated by the function '_read_config_files'.)
CONFIG_FILES_READ = []

_CP = ConfigParser.SafeConfigParser()

def _read_config_files(paths_to_try):
  fnames_to_try = [os.path.join(p, _CONFIG_FNAME) for p in paths_to_try]

  # Try the filenames one-by-one, to enable us to report if any particular file
  # cannot be opened.
  for fname in fnames_to_try:
    try:
      if _CP.read(fname):
        CONFIG_FILES_READ.append(fname)
    except:
      raise CannotOpenFile(fname)

  if not CONFIG_FILES_READ:
    raise MissingDistilConfigFile(_CONFIG_FNAME)

_read_config_files(_CONFIG_PATHS_TO_TRY)

_SECTION = "Distil"


# The absolute (filesystem) path to the base of the "doclib" (document library)
# -- the directory, somewhere in an existing Git repository, in which Distil
# stores all the bib-files, documents, wiki-pages, auto-generated indices, etc.
#
# If the path begins with '~', this will be expanded to the appropriate user
# home-dir (according to the interpretation of 'os.path.expanduser').
#
# For example: /var/lib/distil/doclib (or) ~/Thesis/doclib
DOCLIB_BASE_ABSPATH = os.path.expanduser(_CP.get(_SECTION, 'doclib_base_abspath'))


# A unique name (identifier) for this doclib.  This name should consist only of
# letters, numbers, hyphens, periods and underscores (any other characters will
# be removed).
#   
# For now, this name is only used as the name of the symlink (in the "static"
# directory) to the DOCLIB_BASE_ABSPATH, enabling a single Distil installation
# to be used for multiple doclibs (by running multiple webservers in the same 
# installation).
#
# In the future (ie, when I get around to it), this will also be incorporated
# into the URL path and password authentication, for the rest of what's needed
# to allow multiple Distil instances to run on the same system (on the same port).
# Currently, the password authentication part isn't handled (oops), but you can
# run multiple Distil instances simultanously by running them on different ports.
DOCLIB_IDENTIFIER = re.sub("[^a-zA-Z0-9._-]+", "", _CP.get(_SECTION, 'doclib_identifier'))
DOCLIB_SYMLINK_NAME = "doclib.%s" % DOCLIB_IDENTIFIER


# The location of the Git executable.
#
# For example: /usr/bin/git
GIT_EXECUTABLE = _CP.get(_SECTION, 'git_executable')


# The "cookie_secret" secret key to be supplied to Tornado for secure cookies:
#  http://www.tornadoweb.org/documentation#cookies-and-secure-cookies
#
# To generate an appropriate value for this variable, perform the following
# operations in the Python interpreter:
#
#   import base64
#   import uuid
#   base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
#
# then copy-and-paste the resulting string into your ".distil.cfg" (and ensure
# the file permissions don't allow anyone other than you to read the file).
#
# (This method was recommended by Bret Taylor on 19th Sept, 2009, to generate
# "256 bits of randomness":
#  http://groups.google.com/group/python-tornado/browse_thread/thread/9ea50651adee1150 )
#
# This method will generate a different "unique" value every time you run it.
#
# If you don't specify a value for this variable, Distil will use this method
# to generate a secret key for you automatically, each time Distil is started.
# While this is convenient to get Distil up-and-running quickly, the downside
# is that the secret key will be different every time Distil is started, so
# your users will need to re-login every time Distil is re-started.
COOKIE_SECRET = _CP.get(_SECTION, 'cookie_secret')
if not COOKIE_SECRET:
  print 'Generating a new "cookie secret" secret key.\nThis will invalidate all current login sessions.'
  print '(To prevent this from occurring every time Distil is re-started,\nset a permanent cookie_secret value in ".distil.cfg".)'
  COOKIE_SECRET = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)


# The absolute (filesystem) path to an "htpasswd" file (including the filename)
# that contains the usernames and (SHA-1) htpasswd-encrypted passwords of
# authenticated Distil users.  (Ensure that the file permissions don't allow
# anyone other than you to read the file.)
#
# To create and edit this file, you can use the Apache 'htpasswd' utility.
# For SHA-1 password encryption, supply the "-s" command-line option.
#
# If the path begins with '~', this will be expanded to the appropriate user
# home-dir (according to the interpretation of 'os.path.expanduser').
#
# For example: /var/lib/distil/.htpasswd (or) ~/.distil-htpasswd
HTPASSWD_ABSPATH = os.path.expanduser(_CP.get(_SECTION, 'htpasswd_abspath'))

