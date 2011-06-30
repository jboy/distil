#!/usr/bin/env python
#
# export_bibs_command.py: Export all bibs to an output file.
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
import sys

from distil import config, constants, unicode_string_utils


# Messages to the user.

MISSING_FILENAME = """%s: missing output filename for bibliography
Try `%s --help' for more information."""

USAGE = """Usage: %s [-o OUTFILE]
Export all bibs to stdout, or to OUTFILE if the -o flag is supplied."""

TOO_MANY_ARGS = """%s: too many arguments supplied
Try `%s --help' for more information."""

BAD_ARGS = """%s: invalid arguments supplied
Try `%s --help' for more information."""



def main():
  global PROGNAME

  PROGNAME = sys.argv[0]

  num_args = len(sys.argv) - 1
  if num_args == 0:
    output = sys.stdout
  else:
    arg1 = sys.argv[1]
    if arg1 == "--help":
      # Request for usage information.
      print USAGE % PROGNAME
      sys.exit(0)
    elif arg1 == "-o":
      if num_args < 2:
        # Missing the filename arg.
        print >> sys.stderr, MISSING_FILENAME % (PROGNAME, PROGNAME)
        sys.exit(1)
      if num_args > 2:
        # Too many command-line args.
        print >> sys.stderr, TOO_MANY_ARGS % (PROGNAME, PROGNAME)
        sys.exit(1)

      output = open(sys.argv[2], 'w')
    else:
      # Bad command-line arg...
      print >> sys.stderr, BAD_ARGS % (PROGNAME, PROGNAME)
      sys.exit(1)

  export_bibs(output)


def export_bibs(output):
  # Traverse all bibs in the doclib.
  bibs_subdir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR)
  all_cite_key_subdirs = os.listdir(bibs_subdir_abspath)
  for cite_key in all_cite_key_subdirs:
    export_bib(cite_key, bibs_subdir_abspath, output)


def export_bib(cite_key, bibs_subdir_abspath, output):
  bib_abspath = os.path.join(bibs_subdir_abspath, cite_key, cite_key + ".bib")
  (s, contains_non_ascii, errors) = unicode_string_utils.open_file_read_unicode(bib_abspath)
  if errors:
    for e in errors:
      print >> sys.stderr, e

  print >> output, s.replace('\r\n', '\n').replace('\r', '\n').rstrip().encode('utf8')


if __name__ == "__main__":
  main()

