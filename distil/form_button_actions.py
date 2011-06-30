# form_button_actions.py: Actions for various buttons in the web-forms.
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


import topic_tag_file_io


class WikiButtonActions(object):
  def __init__(self, title, name, get_wiki_text_func, update_wiki_text_func):
    self.title = title
    self.name = name

    # A function that gets the wiki text for a given wiki ID (which may be a cite-key or a wiki-word).
    # Expected parameters: f(wiki_id)
    self.get_wiki_text_func = get_wiki_text_func

    # A function that updates the wiki text for a given wiki ID (which may be a cite-key or a wiki-word).
    # Expected parameters: f(wiki_id, new_text, change_descr)
    self.update_wiki_text_func = update_wiki_text_func
    self.other_unsaved_form_data_to_retain = []

  def preview_wiki_text(self, handler, wiki_id, render_page_args):
    self.set_args_wiki_text(render_page_args, self.get_wiki_text(handler))
    self.set_args_change_descr(render_page_args, self.get_change_descr(handler))
    self.set_args_message_class(render_page_args, "message-preview")
    self.set_args_message(render_page_args, "Preview of %s" % self.title)

    for func in self.other_unsaved_form_data_to_retain:
      func(handler, wiki_id, render_page_args)

  def reset_wiki_text(self, handler, wiki_id, render_page_args):
    self.set_args_message_class(render_page_args, "message-reset")
    self.set_args_message(render_page_args, "%s Reset" % self.title)

    for func in self.other_unsaved_form_data_to_retain:
      func(handler, wiki_id, render_page_args)

  def save_wiki_text(self, handler, wiki_id, render_page_args):
    wiki_text = self.get_wiki_text(handler)
    if wiki_text != self.get_wiki_text_func(wiki_id):
      # The wiki-text has been changed.  So we should save it.
      self.update_wiki_text_func(wiki_id, wiki_text,
          handler.get_input_text("%s-change-descr" % self.name))
      self.set_args_message_class(render_page_args, "message-saved")
      self.set_args_message(render_page_args, "%s Saved!" % self.title)
    else:
      # The wiki-text has not been changed.  So we do nothing.
      self.set_args_change_descr(render_page_args, self.get_change_descr(handler))
      self.set_args_message_class(render_page_args, "message-no-change")
      self.set_args_message(render_page_args, "No Changes to %s" % self.title)

    for func in self.other_unsaved_form_data_to_retain:
      func(handler, wiki_id, render_page_args)

  def retain_unsaved_wiki_text(self, handler, wiki_id, render_page_args):
    # Retain any unsaved text in the wiki-text textarea, or in the "change-descr" field.
    self.set_args_wiki_text(render_page_args, self.get_wiki_text(handler))
    self.set_args_change_descr(render_page_args, self.get_change_descr(handler))

  def set_args_wiki_text(self, render_page_args, text):
    render_page_args[self.name] = text

  def set_args_change_descr(self, render_page_args, change_descr):
    render_page_args["%s_change_descr" % self.name] = change_descr

  def set_args_message_class(self, render_page_args, message_class):
    render_page_args["%s_message_class" % self.name] = message_class

  def set_args_message(self, render_page_args, message):
    render_page_args["%s_message" % self.name] = message

  def get_wiki_text(self, handler):
    return handler.get_textarea_text(self.name)

  def get_change_descr(self, handler):
    return handler.get_input_text("%s-change-descr" % self.name)


class TagButtonActions(object):
  def __init__(self):
    self.other_unsaved_form_data_to_retain = []

  def save_tags(self, handler, cite_key, render_page_args):
    topic_tag_file_io.update_topic_tags_for_cite_key(cite_key,
        handler.get_arguments("tag"), handler.get_input_text("new-tags"))
    render_page_args["tags_message_class"] = "message-saved"
    render_page_args["tags_message"] = "Tags Saved!"

    for func in self.other_unsaved_form_data_to_retain:
      func(handler, cite_key, render_page_args)

  def retain_unsaved_tags(self, handler, cite_key, render_page_args):
    # Retain any unsaved topic tags, and any text in the "new-tags" text field.
    render_page_args["tags"] = handler.get_arguments("tag")
    render_page_args["new_tags"] = handler.get_input_text("new-tags")

