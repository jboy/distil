# htpasswd.py: Functions for compatibility with Apache's 'htpasswd' utility.
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
import hashlib


SHA_PREFIX = "{SHA}"


def check_username_password_authentication(username, password, htpasswd_fname):
  htpasswd_entries = read_htpasswd_entries(htpasswd_fname)
  matching_username_entries = [e for e in htpasswd_entries if e[0] == username]
  if matching_username_entries:
    # FIXME:  Ensure that 'pwhash_in_file' was encrypted using SHA-1.
    # (ie, check that the pwhash starts with 'SHA_PREFIX')

    # FIXME:  Support other types of encryption?  (eg, crypt, MD5)
    # Apache documentation:
    #  http://httpd.apache.org/docs/2.2/misc/password_encryptions.html
    # Example code that supports crypt:
    #  http://trac.edgewall.org/browser/trunk/contrib/htpasswd.py

    pwhash_in_file = matching_username_entries[0][1]
    pwhash_now = encrypt_password_using_sha1(password)
    if pwhash_in_file == pwhash_now:
      return True

  return False


def read_htpasswd_entries(htpasswd_fname):
  entries = []
  lines = open(htpasswd_fname).readlines()
  for line in lines:
    (username, pwhash) = line.rstrip().split(':', 1)
    entries.append((username, pwhash))
  return entries


def encrypt_password_using_sha1(password):
  return SHA_PREFIX + base64.b64encode(hashlib.sha1(password).digest())

