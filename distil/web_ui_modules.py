# web_ui_modules.py: Classes deriving from Tornado's web.UIModule.
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


import tornado.web

class WikiArea(tornado.web.UIModule):
  def render(self, params):
    return self.render_string("ui-module-wiki-area.html", **params)


class CreateAttachmentForm(tornado.web.UIModule):
  def render(self, params):
    return self.render_string("ui-module-create-attachment-form.html", **params)

