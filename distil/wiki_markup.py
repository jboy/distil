# wiki_markup.py: Process wiki markup and render as HTML.
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
import string
import re
import os
import itertools

from xml.sax.saxutils import escape as xml_escape

import config
import constants
import unicode_string_utils


# You probably don't want to edit any of these...
CURRENT_LIST_NESTING = "CURRENT_LIST_NESTING"

# Open/close tags.
# FIXME:  We can do these more minimally, in the style of the list tags below.
BEGIN_BOLD = "<b>"
END_BOLD = "</b>"
BEGIN_ITALIC = "<i>"
END_ITALIC = "</i>"
BEGIN_CODE = "<code>"
END_CODE = "</code>"

# List tags.
ITEMIZE = "ul"
ENUMERATE = "ol"


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class InputSyntaxError(Error):
  """An exception for syntax errors encountered when parsing wiki input.

  It is modelled upon the built-in Python SyntaxError.
  """
  def __init__(self, message, line_num, text, text_start, text_end):
    self.message = message
    self.line_num = line_num
    self.text = text
    self.text_start = text_start
    self.text_end = text_end

  def __str__(self):
    return self.message


def read_wiki_lines_and_transform(f, state):
  output_lines = []
  if not state.has_key(CURRENT_LIST_NESTING):
    state[CURRENT_LIST_NESTING] = []

  BEGIN_PREFORMAT = '{{{'
  END_PREFORMAT = '}}}'
  preformatted_text = False

  line_num = 0
  for line in f:
    line_num += 1

    s = line.rstrip()

    # First, we need to pass any preformatted (raw HTML) text unchanged.
    # We only recognise the beginning of preformatted text ('{{{') at the start of the line.
    if s.startswith(BEGIN_PREFORMAT):
      preformatted_text = True
      # For convenience, we allow preformatted text to continue on the same line as the '{{{'.
      # But if there is no text after the '{{{', don't output an empty line.
      s = s[len(BEGIN_PREFORMAT):]
      if not s:
        continue

    if preformatted_text:
      # Allow text before the end of the preformatted text ('}}}') on the line, but not after.
      # Anything before the '}}}' (ignoring empty text) will be output as preformatted text.
      # Note that we ignore nesting of '{{{' within preformatted text.
      if s.find(END_PREFORMAT) != -1:
        # We end the preformatted text somewhere in this line.
        preformatted_text = False
        parts = s.partition(END_PREFORMAT)
        before_end = parts[0].rstrip()
        if before_end:
          output_lines.append(before_end)
      else:
        # Continue with the preformatted text.
        # Note that we output all preformatted text which is not on the same line as the
        # beginning or end markers, even if it's an empty line.
        output_lines.append(s)
      continue

    if not s:
      # Empty line
      close_any_lists(output_lines, state)
      output_lines.append(s)
      continue

    s = apply_line_filters(s, line_num, output_lines, state)
    output_lines.append(s)

  close_any_lists(output_lines, state)
  return markup_paragraphs(output_lines)


BLOCK_OPEN_TAG_PATTERNS = re.compile(r'^<ol>|^<ul>|^<h\d>')
BLOCK_CLOSE_TAG_PATTERNS = re.compile(r'</ol>$|</ul>$|</li>$|</h\d>$')

def markup_paragraphs(lines):
  if not lines:
    # Nothing to do.
    return lines

  # Otherwise, we know that 'lines' is a non-empty list.
  result_lines = []

  # Open paragraphs where appropriate.
  curr = lines[0]
  if curr and not BLOCK_OPEN_TAG_PATTERNS.search(curr):
    curr = '<p>' + curr
  result_lines.append(curr)

  for prev, curr in pairs(lines):
    if not curr:
      # Nothing to do for empty line.
      pass
    elif BLOCK_OPEN_TAG_PATTERNS.search(curr):
      # This line is already starting a list or heading, so no need to start a paragraph.
      pass
    elif prev:
      # The previous line is not empty, so we don't need to wonder whether
      # this line is the start of a block of text.
      pass
    else:
      curr = '<p>' + curr
    result_lines.append(curr)

  lines = result_lines
  result_lines = []

  # Close paragraphs where appropriate.
  for curr, next in pairs(lines):
    if not curr:
      # Nothing to do for empty line.
      pass
    elif BLOCK_CLOSE_TAG_PATTERNS.search(curr):
      # This line is already ending a list or heading, so no need to end a paragraph.
      pass
    elif next and not BLOCK_OPEN_TAG_PATTERNS.search(next):
      # The next line is neither empty nor the start of a list or heading,
      # so we don't need to wonder whether this line is the end of a block of text.
      pass
    else:
      curr = curr + '</p>'
    result_lines.append(curr)

  curr = lines[-1]
  if curr and not BLOCK_CLOSE_TAG_PATTERNS.search(curr):
    curr = curr + '</p>'
  result_lines.append(curr)
    
  return result_lines


def pairs(s):
  """Given an iterable sequence 's', return an iterable object of all pairs of adjacent elements.
  
  s -> (s0, s1), (s1, s2), (s2, s3), ...

  If 's' contains fewer than two elements, an iterable object of no iterations will be returned.

  Recommended by http://stackoverflow.com/questions/5434891/iterate-a-list-as-pair-current-next-in-python
  """
  a, b = itertools.tee(s)
  next(b, None)
  return itertools.izip(a, b)


def escape_html_entities(s, line_num, output_lines, state):
  return xml_escape(s)


def convert_dashes(s, line_num, output_lines, state):
  # Convert double-hyphens, or single hyphens surrounded by spaces, to em-dashes.
  s = s.replace('--', '&mdash;')
  s = re.sub(r'(\s)-(\s)', r'\1&mdash;\2', s)

  # Convert hyphens in numeric ranges to en-dashes.
  s = re.sub(r'(\d)-(\d)', r'\1&ndash;\2', s)

  return s


# Edit these two as appropriate.
HIGHEST_HEADING_IMPORTANCE = 3  # ie, <h3>
NUM_HEADING_LEVELS_ALLOWED = 4  # ie, <h3>, <h4>, <h5>, etc.

# Hopefully no need to edit these two.
HEADING_REGEX = '^={%d}(.*)={%d}$'
HEADINGS_TO_MATCH = [
  (re.compile(HEADING_REGEX % (i, i)),
  "<h%d>" % (i + HIGHEST_HEADING_IMPORTANCE - 1),
  "</h%d>" % (i + HIGHEST_HEADING_IMPORTANCE - 1))
  for i in xrange(4, 0, -1)
]


def process_headings(s, line_num, output_lines, state):
  for pattern, open_tag, close_tag in HEADINGS_TO_MATCH:
    match = pattern.match(s)
    if match:
      close_any_lists(output_lines, state)
      heading_text = match.group(1).strip()
      return "".join([open_tag, heading_text, close_tag])

  return s


LIST_TYPES = [
  (re.compile(r' (?P<spaces>(?:  )*)\*'),    ITEMIZE),
  #(re.compile(r' (?P<spaces>(?:  )*)\#'),    DENSE_ENUMERATE),
  (re.compile(r' (?P<spaces>(?:  )*)\d+\.'), ENUMERATE)
]


def process_lists(s, line_num, output_lines, state):
  for (regexp, list_type) in LIST_TYPES:
    regexp_matches = regexp.match(s)
    if regexp_matches:
      spaces = regexp_matches.group("spaces")
      # List depth >= 1, where 1 is the most shallow level of list.
      list_depth = (len(spaces) / 2) + 1
      if len(state[CURRENT_LIST_NESTING]) > list_depth:
        # We're already in nested sub-lists, which we need to close to get back to this depth.
        close_any_lists(output_lines, state, list_depth)
      elif len(state[CURRENT_LIST_NESTING]) < list_depth:
        # We need to start a list.
        open_a_list(list_type, line_num, output_lines, state)

      # Now finally we can output the actual list item.
      length_of_match = regexp_matches.end(0)
      return '<li>' + s[length_of_match:].strip() + '</li>'

  # If we got to here, there were no regexp matches, so it can't be a list item.
  # But first, we should check if there was indentation, and complain if there was.
  if s.startswith(' '):
    raise InputSyntaxError("Cannot indent text if not followed by a list item",
        line_num, s, 0, len(s) - len(s.lstrip()))

  return s


def open_a_list(list_type, line_num, output_lines, state):
  state[CURRENT_LIST_NESTING].append(list_type)
  output_lines.append("<%s>" % list_type)


# This approach inspired by Tim Dawborn's "wikiprocessor.py".
def make_bold(obj):
  return '%s%s%s' % (BEGIN_BOLD, obj.group('text'), END_BOLD)

def make_italic(obj):
  return '%s%s%s' % (BEGIN_ITALIC, obj.group('text'), END_ITALIC)

def make_monospace(obj):
  # FIXME:  This function really should ensure (somehow) that no other processing is performed
  # upon this text.
  return '%s%s%s' % (BEGIN_CODE, obj.group('text'), END_CODE)

def make_cite(obj):
  def exists(ck):
    ck_dir_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.BIBS_SUBDIR, ck)
    return os.path.exists(ck_dir_abspath)

  def make_url(ck):
    return '/bib/' + ck

  cite_key = obj.group('text')
  if exists(cite_key):
    link_class = "wiki-normal"
  else:
    link_class = "wiki-not-found"

  return '<a class="%s" href="%s">%s</a>' % (link_class, make_url(cite_key), cite_key)

# See http://en.wikipedia.org/wiki/Percent-encoding#Types_of_URI_characters
# and http://tools.ietf.org/html/rfc3986#section-2.2
# In theory, colons are also a problem, but I intend to handle them specially later
# as namespaces... somehow (perhaps converting "foo:bar" to "foo/bar", for example).
# For now, I just have to make sure I URL-encode them.
ALLOWED_PUNCTUATION = "-_.:"
STRIP_PUNCTUATION_AND_WHITESPACE = \
    unicode_string_utils.StripPunctuationAndWhitespace(ALLOWED_PUNCTUATION)

def make_wikilink(obj):
  def normalise(ww):
    return STRIP_PUNCTUATION_AND_WHITESPACE(unicode(ww.lower().replace(' ', '-')))

  def exists(ww):
    ww_fname_abspath = os.path.join(config.DOCLIB_BASE_ABSPATH, constants.WIKI_SUBDIR, ww)
    return os.path.exists(ww_fname_abspath)

  def make_url(ww):
    return '/wiki/' + ww

  wiki_word = obj.group('text')
  normalised_ww = normalise(wiki_word)
  if exists(normalised_ww):
    link_class = "wiki-normal"
  else:
    link_class = "wiki-not-found"

  return '<a class="%s" href="%s">%s</a>' % (link_class, make_url(normalised_ww), wiki_word)

def make_url(obj):
  url = obj.group('text')
  return '<a class="%s" href="%s">%s</a>' % ("external", url, url)

def make_footnote(obj):
  return r'\footnote{%s}' % obj.group('text').strip()

def make_email(obj):
  return r'{\small {\tt %s}}' % obj.group('text').strip()

RECOGNISED_MARKUP = [
  # Match "non-greedily" between the start and end "**", using ".+?" rather than ".+".
  (re.compile(r'\*\*(?P<text>.+?)\*\*'), make_bold),

  # The extra-complicated regex for italics is to avoid matching a colon (":") before the "//"
  # (which would occur in "http://", "ftp://" and "file://", for example).
  (re.compile(r'(?<!:)//(?P<text>.+?)(?<!:)//'), make_italic),
  (re.compile(r'`(?P<text>[^`]+)`'), make_monospace),

  # A minor extension of the Trac syntax, to support citations to other entries.
  (re.compile(r'\[cite:(?P<text>.+?)\]', re.I), make_cite),

  # A minor extension of the Trac syntax, to support wiki-links.
  (re.compile(r'\[(?P<text>.+?)\]', re.I), make_wikilink),

  # Excuse the fairly arbitrary definition of which characters a URL can contain, or where
  # a URL ends...
  (re.compile(r'(?P<text>http://(?:[^][{}()<> ,.;:!?"]|[,;:!?](?! )|[.](?![.]))+)'), make_url),

  # A minor extension of the Trac syntax, to support footnotes.
  #(re.compile(r'\[\[Footnote\((?P<text>.+?)\)\]\]', re.I), make_footnote),

  # A minor extension of the Trac syntax, to support email addresses.
  #(re.compile(r'\[\[Email\((?P<text>.+?)\)\]\]', re.I), make_email),
]


def process_style_markup(s, line_num, output_lines, state):
  for (regexp, markup) in RECOGNISED_MARKUP:
    s = regexp.sub(markup, s)

  return s


ABBREV_MAPPINGS = [
  ("etc.", "<i>etc</i>."),

  ("eg,", "<i>eg</i>,"),
  ("eg.", "<i>eg</i>."),

  ("ie,", "<i>ie</i>,"),
  ("ie.", "<i>ie</i>."),

  ("vs ", "<i>vs</i> "),
  ("vs.", "<i>vs</i>."),

  ("aka ", "<i>aka</i> "),
  ("aka.", "<i>aka</i>."),
]


def process_abbrevs(s, line_num, output_lines, state):
  for raw_text, styled_abbrev in ABBREV_MAPPINGS:
    s = s.replace(raw_text, styled_abbrev)

  return s


ARROW_MAPPINGS = [
  # The '>' characters in these have already been by 'xml_escape',
  # so we need to look for '&gt;' rather than '>'.
  ('&lt;-&gt;',   '&harr;'),  # '<->'
  ('&lt;--&gt;',  '&harr;'),  # '<-->'
  ('&lt;=&gt;',   '&hArr;'),  # '<=>'
  ('&lt;==&gt;',  '&hArr;'),  # '<==>'
  ('-&gt;',       '&rarr;'),  # '->'
  ('=&gt;',       '&rArr;'),  # '=>'
  ('&gt;&gt;',    '&raquo;'),  # '>>'
]


def convert_multi_char_seqs(s, line_num, output_lines, state):
  s = s.replace('...', '&hellip;')

  for wiki_arrow, html_arrow in ARROW_MAPPINGS:
    s = s.replace(wiki_arrow, html_arrow)

  return s


def convert_double_quotes(s, line_num, output_lines, state):
  """Convert double-quote characters to HTML-friendly "&ldquo;" or "&rdquo;" as appropriate."""

  # The heuristic we use is:
  #  1. If it's at the start of the line, or preceded by a space, or preceded by a left-paren,
  #     assume it's the beginning of a quote, and replace with "&ldquo;".
  #  2. Otherwise, assume it's a closing-quote, and replace with "&rdquo;".
  s = re.sub('^"', '&ldquo;', s)
  s = re.sub('([ (])"', r'\1&ldquo;', s)
  s = re.sub(r'"', "&rdquo;", s)

  return s


LINE_FILTERS = [
  escape_html_entities,

  # This should be before handling of style markup, since this will
  # convert double-quotes to HTML entities (which will break the hyperlinks
  # created by the style markup.
  convert_double_quotes,

  process_headings,
  process_lists,
  process_style_markup,

  process_abbrevs,
  # multi-char-seqs need to be converted before dashes, since we want '<-->'
  # to be considered a multi-char seq rather than a dash.
  convert_multi_char_seqs,
  convert_dashes,
]

def apply_line_filters(s, line_num, output_lines, state):
  for f in LINE_FILTERS:
    s = f(s, line_num, output_lines, state)

  return s


def close_any_lists(output_lines, state, target_depth=0):
  while len(state[CURRENT_LIST_NESTING]) > target_depth:
    output_lines.append('</%s>' % state[CURRENT_LIST_NESTING][-1])
    state[CURRENT_LIST_NESTING].pop()

