#!/usr/bin/env python
#
# import_bib_command.py: Import bibs through a command-line interface.
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


import sys
import collections
import itertools

from distil import stored_bibs, filesystem_utils


# Internal constants -- don't edit.
BIB_FNAME = 1
DOC_FNAME = 2
ABS_FNAME = 3

FTYPE_DESCR = {
  BIB_FNAME: "BibTeX file",
  DOC_FNAME: "document",
  ABS_FNAME: "abstract",
}


# You can switch this off if you want, but why would you want to?
SANITY_CHECK_SUFFIXES = True

# Add to these per-filetype sets as necessary.
# Note that you must include the period (".") before the suffix,
# unless you want to allow _no_suffix_, in which case supply "".
EXPECTED_SUFFIXES = {
  BIB_FNAME: set([".bib"]),
  DOC_FNAME: set([".pdf", ".ps.gz", ".ps.bz2"]),
  ABS_FNAME: set(["", ".abs", ".abstract", ".txt"]),
}


# Messages to the user.

MISSING_FILENAME = """%s: missing BibTeX filename
Try `%s --help' for more information."""

USAGE = """Usage: %s BIB [DOC [ABSTRACT]]
Import BibTeX file BIB, plus document DOC and abstract ABS file if specified."""

ARG_ERROR = """%s: error: supplied file '%s' as a %s argument.
Try `%s --help' for more information."""

ARG_WARNING = """%s: unrecognised suffix on file '%s' supplied as %s argument.
Try `%s --help' for more information."""


def main():
  global PROGNAME

  PROGNAME = sys.argv[0]
  if len(sys.argv) == 1:
    # Missing any command-line args.
    print >> sys.stderr, MISSING_FILENAME % (PROGNAME, PROGNAME)
    sys.exit(1)

  if sys.argv[1] == "--help":
    # Request for usage information.
    print USAGE % PROGNAME
    sys.exit(0)

  args = parse_commandline_args(sys.argv[1:])
  if SANITY_CHECK_SUFFIXES:
    sanity_check_suffixes(args)
  stored_bibs.store_new_bib(args[BIB_FNAME], args[DOC_FNAME], args[ABS_FNAME])


def sanity_check_suffixes(args):
  # Initialisation of data-structures that will be used for all sanity checks.
  all_suffixes = set(itertools.chain(*EXPECTED_SUFFIXES.values()))
  unexpected_suffixes = {}
  for ftype in EXPECTED_SUFFIXES.keys():
    unexpected_suffixes[ftype] = all_suffixes - EXPECTED_SUFFIXES[ftype]

  # Now into the sanity checks...
  for ftype in EXPECTED_SUFFIXES.keys():
    if args.has_key(ftype):
      fname = args[ftype]
      suffix = filesystem_utils.get_suffix(fname, allow_absent_suffix=True).lower()

      if suffix in unexpected_suffixes[ftype]:
        # This is clearly an error.
        print >> sys.stderr, ARG_ERROR % \
            (PROGNAME, fname, FTYPE_DESCR[ftype], PROGNAME)
        sys.exit(1)
      if suffix not in EXPECTED_SUFFIXES[ftype]:
        # This is strange.
        print >> sys.stderr, ARG_WARNING % \
            (PROGNAME, fname, FTYPE_DESCR[ftype], PROGNAME)
        sys.exit(1)


def parse_commandline_args(commandline_args):
  args = collections.defaultdict(lambda: None)

  if len(commandline_args) > 0:
    args[BIB_FNAME] = commandline_args[0]
  if len(commandline_args) > 1:
    args[DOC_FNAME] = commandline_args[1]
  if len(commandline_args) > 2:
    args[ABS_FNAME] = commandline_args[2]

  return args


if __name__ == "__main__":
  main()

