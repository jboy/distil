#!/usr/bin/env python
#
# import_attachment_command.py: Import attachments through a command-line interface.
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

from distil import attachments


# Messages to the user.

MISSING_FILENAME = """%s: missing attachment filename
Try `%s --help' for more information."""

USAGE = """Usage: %s ATTACHMENT
Import ATTACHMENT."""


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

  for arg in sys.argv[1:]:
    attachments.store_new_attachment(arg)


if __name__ == "__main__":
  main()

