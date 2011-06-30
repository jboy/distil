# test_framework.py: A simple test framework.
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


def test_and_compare(tests, fn, descr):
  """Expect 'tests' to be a list of pairs (input, expected output)."""

  for input, expected_output in tests:
    result = fn(input)
    if result != expected_output:
      print "%s test failed: expected '%s' -> '%s': got '%s'" % \
          (descr, input, expected_output, result)


def test_and_compare_and_catch(tests, fn, descr):
  """Expect 'tests' to be a list of triples (input, expected output, expected exception)."""

  for input, expected_output, expected_ex in tests:
    if expected_ex:
      try:
        result = fn(input)
      except Exception as ex:
        if str(ex) != str(expected_ex):
          print "%s test failed: expected '%s' to throw '%s': caught '%s'" % \
              (descr, input, expected_ex, ex)
        continue
      print "%s test failed: expected '%s' to throw '%s': no exception thrown" \
          % (descr, input, expected_ex)
    else:
      result = fn(input)
      if result != expected_output:
        print "%s test failed: expected '%s' -> '%s': got '%s'" % \
            (descr, input, expected_output, result)

