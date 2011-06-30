# abstract_file_io.py: File I/O for abstracts.
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

import config
import constants


def get_abstract_for_cite_key(cite_key):
  abstract_fname_abspath = \
    os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, cite_key, constants.ABSTRACT_FNAME)
  if os.path.exists(abstract_fname_abspath):
    return open(abstract_fname_abspath).read().strip()
  else:
    return ""

