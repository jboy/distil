#!/usr/bin/env python #
# webserver.py: A webserver for the Distil web-interface.
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
import os

import tornado.autoreload

from tornado import options
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

from distil import config, constants, web_request_handlers, web_ui_modules


# Define the command-line options.
options.define("port", default=8888, help="Specify the port on which to listen.", type=int)


HANDLERS = [
  # Unauthenticated URLs:
  (r"/login",                       web_request_handlers.LoginHandler),
  (r"/logout",                      web_request_handlers.LogoutHandler),

  # Authenticated URLs:
  (r"/",                            web_request_handlers.MainHandler),
  (r"/attachments",                 web_request_handlers.AttachmentsHandler),
  (r"/attachment/([a-zA-Z0-9]+)",   web_request_handlers.AttachmentXHandler),
  (r"/cite-keys",                   web_request_handlers.CiteKeysHandler),
  (r"/bib/([a-z0-9-]+)",            web_request_handlers.BibXHandler),
  (r"/tag/([a-z0-9-_+.:]+)",        web_request_handlers.TagXHandler),
  (r"/wiki-words",                  web_request_handlers.WikiWordsHandler),
  (r"/wiki-create",                 web_request_handlers.WikiCreateHandler),
  (r"/wiki/([a-z0-9-_+.:]+)",       web_request_handlers.WikiXHandler),
]

SETTINGS = dict(
  # This first setting ("autoescape=None") is recommended by the Tornado 2.0
  # release notes, and seems to be necessary if I want my 1.x-era templates
  # to work with Tornado 2.0.
  # http://www.tornadoweb.org/documentation/releases/v2.0.0.html
  #
  # (The alternative is to update my templates so they no longer work with
  # Tornado 1.x... which obviously I'll do eventually, but maybe not just yet.)
  autoescape=None,
  cookie_secret=config.COOKIE_SECRET,
  login_url="/login",
  static_path=os.path.join(os.path.dirname(__file__), "static"),
  template_path=os.path.join(os.path.dirname(__file__), "templates"),
  ui_modules=web_ui_modules,
  xsrf_cookies=True,
  debug=True
)

APPLICATION = tornado.web.Application(HANDLERS, **SETTINGS)


def main():
  options.parse_command_line()
  ensure_symlink_to_doclib()

  http_server = HTTPServer(APPLICATION)

  # "By default, listen() runs in a single thread in a single process.
  # You can utilize all available CPUs on this machine by calling bind()
  # and start() instead of listen()":
  # https://github.com/facebook/tornado/blob/master/tornado/httpserver.py

  print "Listening on port", options.options.port
  http_server.listen(options.options.port)
  print "Service available at http://localhost:8888/"

  io_loop = IOLoop.instance()
  # Automatically restart the server when a module is modified.
  tornado.autoreload.start(io_loop)
  io_loop.start()


def ensure_symlink_to_doclib():
  """Ensure there is a symlink from "static/doclib" to the "document library" (doclib).

  This enables us to serve files from the doclib.

  The filesystem paths to the doclib are specified using the configuration variables
  'DOCLIB_BASE_ABSPATH' and 'BIBS_SUBDIR', which are defined in the file "config.py".

  This symlink should exist every time after the first time this webserver is started,
  but we should still ensure that it exists the first time.
  """

  # First, check that the doclib exists where we expect it to.
  if not os.path.exists(config.DOCLIB_BASE_ABSPATH):
    print >> sys.stderr, 'Error: doclib "%s" does not exist.\nAborting.' % config.DOCLIB_BASE_ABSPATH
    print >> sys.stderr, '\n(To fix this problem, edit "config.py" to correct the configuration variables.)'
    sys.exit(1)

  # Next, create the symlink if nothing exists there.
  symlink_name = "static/" + config.DOCLIB_SYMLINK_NAME
  if not os.path.lexists(symlink_name):
    print 'Creating symlink "%s"' % symlink_name
    os.symlink(config.DOCLIB_BASE_ABSPATH, symlink_name)

  # Finally, check the validity of the symlink.
  if not os.path.exists(symlink_name):
    print >> sys.stderr, 'Error: "%s" is a broken symlink.\nAborting.' % symlink_name
    print >> sys.stderr, '\n(To fix this problem, edit "config.py" to correct the configuration variables,\nand delete the symlink "%s" so it can be re-created.)' % symlink_name
    sys.exit(1)


if __name__ == "__main__":
  main()

