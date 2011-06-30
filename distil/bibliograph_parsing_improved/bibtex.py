############################################################################
#                                                                          #
#             copyright (c) 2003 ITB, Humboldt-University Berlin           #
#             written by: Raphael Ritz, r.ritz@biologie.hu-berlin.de       #
#                                                                          #
############################################################################

"""BibtexParser class"""

import os
import re
import types

from collections import defaultdict

from zope.component import getUtility, ComponentLookupError

from bibliograph.parsing.parsers.base import BibliographyParser
from bibliograph.rendering.interfaces import IBibTransformUtility

from bibliograph.core.utils import _encode, _decode
from bibliograph.core.bibutils import _hasCommands
from bibliograph.core.encodings import _latex2utf8enc_mapping
from bibliograph.core.encodings import _latex2utf8enc_mapping_simple


_encoding = 'utf-8'   # XXX: should be taken from the site configuration
haveBibUtils = _hasCommands('bib2xml')
FIX_BIBTEX = os.environ.has_key('FIX_BIBTEX')


# Added by JB, 2011-06-03.
BIBTEX_ENTRY_TYPES = [
    # The standard BibTeX entry types.
    # (As confirmed by http://www.cs.arizona.edu/~collberg/Teaching/07.231/BibTeX/bibtex.html
    # and Appendix B of ''A Guide to Latex, Third Edition'', 1999, by Helmut Kopka and Patrick W. Daly)
    'article',
    'book',
    'booklet',
    'conference',
    'inbook',
    'incollection',
    'inproceedings',
    'manual',
    'mastersthesis',
    'misc',
    'phdthesis',
    'proceedings',
    'techreport',
    'unpublished',

    # Unofficial extension entry types included in the original version of this parser.
    'collection',
    'patent',
    'webpublished',
]

# Added by JB, 2011-06-03.
BIBTEX_SPECIAL_FEATURES = [
    # Comments and string constants -- not entry types.
    # (See http://www.cs.arizona.edu/~collberg/Teaching/07.231/BibTeX/bibtex.html
    # and http://artis.imag.fr/~Xavier.Decoret/resources/xdkbibtex/bibtex_summary.html )
    'comment',
    'preamble',
    'string',
]


# Added by JB, 2011-06-03.
# These regexes are used by the optimised BibtexParser method 'stripComments'.
START_OF_ENTRY_REGEX = re.compile(r".*?^(?P<start_entry>@[A-Za-z]+[ ]*\{)", re.MULTILINE|re.DOTALL)

COMMON_START_PATTERN = r"(?P<text>[^{}@]*?)(?<!\\)"
EVENT_TYPES_PATTERN = r"(?P<event>\{|\}|\\\\|\\\{|\\\})"
BRACE_AND_BACKSLASH_REGEX = re.compile(COMMON_START_PATTERN + EVENT_TYPES_PATTERN, re.MULTILINE)

AT_SYMBOL_REGEX_NOT_START_OF_LINE = re.compile(r"(?P<text>[^@]*)(?<!\n)@", re.MULTILINE)
SKIP_MANGLED_ENTRY_REGEX =        re.compile(r"[^@]*^(?P<start_entry>@[A-Za-z]+[ ]*\{)", re.MULTILINE)
AT_SYMBOL_REGEX_ANY_POSITION =    re.compile(r"(?P<text>[^@]*)@", re.MULTILINE)


# The impetus behind this optimisation is the observation that in the original
# version of the BibtexParser method 'convertLaTeX2Unicode', 'string.replace'
# was being called 2189 times per invocation of 'convertLaTeX2Unicode'.
# Each 'string.replace' call was to replace a particular LaTeX entity with the
# corresponding Unicode character; each 'string.replace' computation had to
# look through the entire source string.  After 'stripComments' was optimised
# (becoming >6000x faster), 'convertLaTeX2Unicode' by far the slowest function
# (taking almost 100x as long as the next-slowest function, which as it happens
# was 'stripComments').
#
# However, many of the LaTeX entity strings started with the same substrings --
# e.g. '$\\leftthreetimes$', '$\\leftrightarrows$', '$\\leftrightharpoons$' and
# 7 others all started with the substring '$\\left'.  Hence, if this substring
# was not found in the source string, then none of those LaTeX entity strings
# could be in the source string either, and a single pass through the source
# string (looking for the shorter substring) would obviate the need for all the
# other passes (looking for the longer strings).  Furthermore, even if the
# substring *were* found in the string, the search function can short-circuit
# as soon as the substring is found (as opposed to 'string.replace', which must
# process the whole string) so on average only half the source string would be
# searched (if the substring is present).
#
# In terms of numbers, 1434 of the LaTeX entities begin with the 2-character
# substring r'$\', while 700 begin with r'{\'.  Looking at 3-character substrings,
# 855 begin with r'$\m', 212 with r'{\c', 186 with r'{\d', 133 with r'$\E', etc.
# Hence, it becomes apparent how even the extra cost of if-statements and
# recursion can be worth it.
#
# The data-structure built is a list of pairs, where each pair is either the
# same (latex_entity, unicode_character) found in the original mapping; or,
# if 10 or more LaTeX entities begin with the same substring, the first element
# of the pair is the substring, and the second element is a list of pairs
# containing only those LaTeX entities containing that substring.
# The nesting continues recursively for successively longer-length substrings,
# forming a tree.
#
# Overall, this optimisation yielded a 4.5x speedup for the function:
# 1.198 CPU secs per call (on the ~1M benchmark BibTeX file) down to 0.259.

def _build_mapping_tree(mapping_items, N=2):
    all_first_N_chars = defaultdict(list)
    for item in mapping_items:
        all_first_N_chars[item[0][:N]].append(item)

    tree_level_N = []
    for first_N_chars, item_list in all_first_N_chars.items():
        if len(item_list) < 10:
            # There are less than 10 LaTeX entities that begin with
            # this particular substring, so don't bother constructing
            # a sub-tree; just include the pairs directly in the list.
            tree_level_N.extend(item_list)
        else:
            # Recurse to construct a sub-tree with a substring that's
            # 1 character longer than the current substring.
            sub_tree = _build_mapping_tree(item_list, N+1)
            if len(sub_tree) == 1:
                # The first level of the sub-tree doesn't branch (e.g.,
                # it's the substring r'$\lef', but all the LaTeX entities
                # share the same (longer) substring r'$\left', so the
                # branching only happens after r'$\left').
                # Hence, let's skip over the non-branching first level.
                tree_level_N.append((first_N_chars, sub_tree[0][1]))
            else:
                tree_level_N.append((first_N_chars, sub_tree))

    return tree_level_N

# These data structures used by the optimised BibtexParser method 'convertLaTeX2Unicode'.
LATEX2UTF8ENC_MAPPING_TREE = _build_mapping_tree(_latex2utf8enc_mapping.items())
LATEX2UTF8ENC_MAPPING_SIMPLE_TREE = _build_mapping_tree(_latex2utf8enc_mapping_simple.items())


def _replace_using_mapping_tree(s, mapping_tree):
    for k, v in mapping_tree:
        if type(v) == types.ListType:
            # v is a subtree of LaTeX entities; k is the common start of them.
            # Hence, if k is not in s, then none of the entities in v can be.
            if k in s:
                s = _replace_using_mapping_tree(s, v)
        else:
            s = s.replace(k, v)

    return s


class BibtexParser(BibliographyParser):
    """
    A specific parser to process input in BiBTeX-format.
    """

    meta_type = "Bibtex Parser"

    format = {'name':'BibTeX',
              'extension':'bib'}

    def __init__(self,
                 id = 'bibtex',
                 title = "BibTeX parser",
                 delimiter = '}\s*@',
                 pattern = '(,\s*[\w\-]{2,}\s*=)'):
        """
        initializes including the regular expression patterns
        """
        self.id = id
        self.title = title
        self.setDelimiter(delimiter)
        self.setPattern(pattern)


    # Here we need to provide 'checkFormat' and 'parseEntry'
    def checkFormat(self, source):
        """
        is this my format?
        """
        # Pattern improved by JB to allow spaces before the open-brace.
        #pattern = re.compile('^@[A-Z|a-z]*{', re.M)
        #entry_type_regex = re.compile(r'^@[A-Za-z]+[ ]*\{[ ]*[^, ][^,]*,', re.MULTILINE)
        entry_type_regex = re.compile(r'^@([A-Za-z]+)[ ]*\{', re.MULTILINE)
        entry_types_in_file = re.findall(entry_type_regex, source)

        if entry_types_in_file:
            for et in entry_types_in_file:
                et = et.lower()
                if (et not in BIBTEX_ENTRY_TYPES) and (et not in BIBTEX_SPECIAL_FEATURES):
                    return 0
            return 1
        else:
            return 0

    def preprocess(self, source):
        """
        expands LaTeX macros
        removes LaTeX commands and special formating
        converts special characters to their HTML equivalents
        """
        source = self.expandMacros(source)

        # let Bibutils cleanup up the BibTeX mess
        if FIX_BIBTEX and haveBibUtils:
            try:
                tool = getUtility(IBibTransformUtility, name=u"external")
                source = tool.transform(source, 'bib', 'bib')
            except ComponentLookupError:
                pass

        source = self.stripComments(source)
        source = self.convertChars(source)
        # it is important to convertChars before stripping off commands!!!
        # thus, whatever command will be replaced by a unicode value... the
        # remaining LaTeX commands will vanish here...
        source = self.stripCommands(source)
        return source

    def expandMacros(self, source):
        source = self.expandStringMacros(source)
        # add more macro conventions here if there are any
        return source

    def expandStringMacros(self, source):
        lines = source.split('\n')
        macros = []
        sourcelns = []
        for line in lines:
            if line.find('@String') > -1:
                macros.append(line)
            else:
                sourcelns.append(line)
        source = '\n'.join(sourcelns)
        for macro in macros:
            split_on = re.compile('[{=}]+')
            raw_matches = split_on.split(macro)
            matches = [m for m in raw_matches if m not in ['', ' ', '\r']]
            # raise str(matches)
            short = matches[1].strip()
            long = matches[-1].strip()
            pattern = "\\b" + short + "\\b"
            old = re.compile(pattern)
            source = old.sub(long, source)
        return source

    def stripCommands(self, source):
        oldstyle_cmd = re.compile(r'{\\[a-zA-Z]{2,}')
        newstyle_cmd = re.compile(r'\\[a-zA-Z]+{')
        source = oldstyle_cmd.sub('{', source)
        source = newstyle_cmd.sub('{', source)
        return source

    def stripComments(self, source):
        # This function removes any text between (ie, outside of) entries.
        # This function was improved by JB, 2011-06-03.
        #
        # The original function used the O(n^2) string-concatenation anti-pattern.
        # Relevant source excerpts:
        #
        #   newsource = ''
        #   for idx in range(len(source)):
        #     char = source[idx]
        #     # ...
        #     newsource = newsource + char
        #   source = newsource
        #
        # I changed it to append to a list instead, thereby avoiding the O(n^2)
        # string-concatenation anti-pattern:
        #
        #   newsource = []
        #   for idx in range(len(source)):
        #     char = source[idx]
        #     # ...
        #     newsource.append(char)
        #   source = "".join(newsource)
        #
        # This yielded a 128x speedup for the function (profiled by cProfile):
        # 133.083 CPU secs (2 mins 13 secs) per call on the ~1M benchmark BibTeX file,
        # down to 1.037 CPU secs per call.  (While yielding the same output, of course.)
        #
        # The basic algorithm was still:
        #
        #   for each char c in the string source:
        #     if char == '@' and not inside_entry:
        #       inside_entry = True
        #       brace_nesting_level = 0
        #     if inside_entry:
        #       append c to string output
        #       update brace_nesting_level if char is '{' or '}', not preceded by r'\'
        #       if brace_nesting_level is now 0:
        #         inside_entry = False
        #         append newline to string output
        #
        # plus a variable 'waiting_for_first_brace' that was presumably intended
        # to track whether the first brace after the entry-type '@whatever' had
        # been encountered yet.
        #
        # Next, I decided to replace the char-by-char processing with multi-line
        # regexes over the input as a single string.
        #
        # It seemed to me that there are 9 events in which we're interested:
        #  1. r".*?^@([A-Za-z]+[ ]*)\{" to begin an entry, which will only
        #     be checked when the brace nesting level is zero.
        #
        #  2. r"([^{}@]*?)(?<!\\)\{" (ie, anything (except '{', '}' or '@')
        #     which followed by a '{' (which is not preceded immediately by r'\',
        #     instead makes it a literal brace) to increment the brace level.
        #  3. r"([^{}@]*?)(?<!\\)\}" (ie, anything (except '{', '}' or '@')
        #     followed by a '}' (which is not preceded immediately by r'\',
        #     which instead makes it a literal brace) to decrement the brace
        #     level and possibly end the entry.
        #  4. r"([^{}@]*?)(?<!\\)\\\\" to match a double back-slash.
        #  5. r"([^{}@]*?)(?<!\\)\\\{" and
        #  6. r"([^{}@]*?)(?<!\\)\\\}" to match braces that *are* preceded by a
        #     backslash (ie, to make a literal brace) -- as long as the backslash
        #     is not *also* preceded by a backslash.
        #
        # (NOTE:  Technically, the start and end of entries can also be
        # indicated by parens rather than braces, but one step a time...
        # (The original version of the function didn't handle this either...)
        # See http://www.cs.arizona.edu/~collberg/Teaching/07.231/BibTeX/bibtex.html
        # or http://artis.imag.fr/~Xavier.Decoret/resources/xdkbibtex/bibtex_summary.html
        # for more details.)
        #
        # If none of #2-#6 match, there are no braces or double backslashes;
        # perhaps there's an '@' symbol (which can appear at the beginning of
        # a line to indicate a new entry, or anywhere in a line to represent a
        # literal @ symbol):
        #  7. r"([^@]*)(?<!\n)@" to match an at-symbol on the current line
        #     that is not at the beginning of the line.
        # 
        # If none of #2-#7 match, then there's no @ symbol on this line, so
        # maybe there's an @ symbol on the next line.  But maybe it's at the
        # beginning of the line, and it indicates a new entry...
        # Note that, since #1 will consume (and ignore) everything until the
        # "^@" (to ignore the text outside the entry), it should not be invoked
        # unless the brace nesting level is zero.  Hence, we'll also provide an
        # alternative:
        #  8. r"[^@]*^@([A-Za-z]+[ ]*)\{" to skip the rest of a mangled entry
        #     (an entry that is not yet finished, but which contains no more
        #     right-braces to finish it) to recover and reset the parsing.
        # In contrast to #1, #8 will be active when the brace nesting level is
        # NOT zero.
        #
        # Finally, if #8 doesn't work, then it might be an @ symbol that is NOT
        # on this line (hence, #7 won't match), but is also not suitable to
        # start a new entry (hence, #8 won't match).  So, let's just consume
        # everything up-to (and including) this @ symbol, if it's there:
        #  9. r"([^@]*)@"
        #
        # This change yielded another 47x speedup: 1.037 CPU secs per call,
        # down to 0.022 CPU secs per call.  (Output verified to be the same.)
        # The total speedup of the function was now >6000x: 133.083 down to 0.022.

        # Bring global variables into local scope, since they will be accessed repeatedly.
        start_of_entry_regex = START_OF_ENTRY_REGEX
        brace_and_backslash_regex = BRACE_AND_BACKSLASH_REGEX
        at_symbol_regex_not_start_of_line = AT_SYMBOL_REGEX_NOT_START_OF_LINE
        skip_mangled_entry_regex = SKIP_MANGLED_ENTRY_REGEX
        at_symbol_regex_any_position = AT_SYMBOL_REGEX_ANY_POSITION

        complete_entries = []
        current_entry = []
        pos = 0

        m = start_of_entry_regex.match(source)
        while m:
            brace_nesting_level = 1
            current_entry.append(m.group("start_entry"))
            pos = m.end("start_entry")

            while brace_nesting_level > 0:
                m = brace_and_backslash_regex.match(source, pos)
                if m:
                    current_entry.append(m.group("text"))

                    event = m.group("event")
                    current_entry.append(event)
                    pos = m.end("event")

                    if event == "{":
                        brace_nesting_level += 1
                    elif event == "}":
                        brace_nesting_level -= 1

                    continue

                # Else, no braces or double backslashes found.
                # Try the at-symbol regexes.
                m = at_symbol_regex_not_start_of_line.match(source, pos)
                if m:
                    current_entry.append(m.group("text") + '@')
                    pos = m.end("text") + 1
                    continue

                m = skip_mangled_entry_regex.match(source, pos)
                if m:
                    current_entry = []
                    break  # back out to 'while m'

                m = at_symbol_regex_any_position.match(source, pos)
                if m:
                    current_entry.append(m.group("text") + '@')
                    pos = m.end("text") + 1
                    continue

                # Otherwise, we weren't able to match anything...
                # There were no braces or double-backslashes.
                # There were no @ symbols, so we can't reset to another entry.
                current_entry = []
                break  # back out to 'while m'

            # If we're outside the inner while loop, brace_nesting_level == 0.
            # Hence, an entry was completed.
            current_entry.append('\n')
            complete_entries.extend(current_entry)
            current_entry = []
            m = start_of_entry_regex.match(source, pos)

        # If we're outside the outer while loop, there were no (more) entry-starts found.
        # Hence, let's wrap it up and go home.
        source = "".join(complete_entries)
        return source

    def convertChars(self, source):
        source = self.convertLaTeX2Unicode(source)
        source = self.fixWhiteSpace(source)
        return self.explicitReplacements(source)

    def convertLaTeX2Unicode(self, source):
        # This function converts LaTeX entities to Unicode characters.
        # This function was improved by JB, 2011-06-05.
        #
        # Changes:
        #  1. Rather than:
        #     for k in d.keys():
        #       s = s.replace(k, d[k])
        #    use:
        #     for k, v in d.items():
        #       s = s.replace(k, v)
        #
        #  2. Rather than (decode -> replace -> encode) *every* *iteration*,
        #    decode once at the beginning, and encode again once at the end.
        #
        # This yielded an 8x speedup for the function (profiled by cProfile):
        # 9.615 CPU secs per call on the ~1M benchmark BibTeX file (19.230 secs total),
        # down to 1.198 CPU secs/call (2.397 secs total).
        #
        # Next, the functions '_build_mapping_tree' and '_replace_using_mapping_tree'
        # were used to optimise-dowm the number of 'string.replace' calls.
        # (For more info, read the comment immediately above '_build_mapping_tree'.)
        #
        # This optimisation yielded a 4.5x speedup for this function:
        # 1.198 CPU secs per call (on the ~1M benchmark BibTeX file) down to 0.259.
        # The total speedup of this function was now >35x: 9.615 down to 0.259.

        source = _decode(source)
        #for latex_entity, unicode_code_point in _latex2utf8enc_mapping_simple.items():
            #source = source.replace(latex_entity, unicode_code_point)
        source = _replace_using_mapping_tree(source, LATEX2UTF8ENC_MAPPING_SIMPLE_TREE)

        #for latex_entity, unicode_code_point in _latex2utf8enc_mapping.items():
            #source = source.replace(latex_entity, unicode_code_point)
        source = _replace_using_mapping_tree(source, LATEX2UTF8ENC_MAPPING_TREE)
        source = _encode(source)

        return source

    def fixWhiteSpace(self, source):
        ttable = [(r'\ ', ' '),
                  (r'\!', ' '),
                  ]
        source = self.mreplace(source, ttable)
        wsp_tilde = re.compile(r'[^/\\]~')
        return wsp_tilde.sub(self.tilde2wsp, source).replace('\~', '~')

    def tilde2wsp(self, hit): 
        return hit.group(0)[0] + ' '

    def explicitReplacements(self, source):
        # list of 2 tuples; second element replaces first
        ttable = [(r'\/', ''),
                  (r'\&', '&'),
                  (r'\~', '~'),
                  (r'---', '&mdash;'),
                  (r'--', '&ndash;'),
                  ]
        return self.mreplace(source, ttable)

    def mreplace(self, s, ttable):
        for a, b in ttable:
            s = s.replace(a, b)
        return s

    # done with preprocessing

    def parseEntry(self, entry):
        """
        parses a single entry

        returns a dictionary to be passed to
        BibliographyEntry's edit method
        """
        result = {}
        authorlist = []
        authorURLlist = []

        # remove newlines and <CR>s, and remove the last '}'
        entry = entry.replace('\n', ' ').replace('\r', '').replace('\t', ' ').rstrip().rstrip('}')
        tokens = self.pattern.split(entry)
        try:
            type, pid = tokens[0].strip().split('{')
            type = type.replace('@', '').strip().lower()
            result['reference_type'] = type.capitalize() + 'Reference'
            result['pid'] = pid.replace(',', '').strip()
        except:
            return "Bibtex Parser Error: malformed first line."

        for k,v in self.group(tokens[1:],2):
            key = k[1:-1].strip().lower()
            # INBOOKs mapping: title -> booktitle, chapter -> chapter and title
            if type == 'inbook':
                if key == 'title':
                    key = 'booktitle'

                if key == 'chapter':
                    result['title'] = self.cleanLine(v)

            # BibTex field "type" maps to CMFBAT field "publication_type"
            if key == 'type':
                key = 'publication_type'
                result[key] = self.cleanLine(v)

            # special procedure for authors and editors
            elif key == 'author':
                if result.has_key('author'):
                    result[key].append(self.cleanLine(v))
                else:
                    result[key] = [ self.cleanLine(v) ]
            elif (key == 'editor') and (type in ['book','proceedings']):
                if result.has_key('editor'):
                    result[key].append(self.cleanLine(v)) 
                else:
                    result[key] = [self.cleanLine(v)]
            elif key == 'keywords':
                if not result.has_key(key):
                    # Original BibTeX files contain only *one* 'keywords = '
                    # for multiple keywords
                    result[key] = self.splitMultiple(v) 
                else:
                    # This is likely used by other importers/parser trying to mis-use
                    # the BibTeX importer with multiple keywords
                    result[key].append(self.cleanLine(v))
            else:
                value = self.cleanLine(v)
                result[key] = value
                # Aliasing the value to an upper-cased key so that when this dictionary
                # is passed into <a_reference_object>.edit(**dictionary), the values
                # will match and auto-update schema fields that are specified in either
                # upper or lower case.  This is motivated by the 'DOI' field being upper-cased.
                # Of course, this won't help mixed-case fields, but we'd probably need to change
                # Archetype internals to fix that - and that would be a questionable endeavour.
                result[key.upper()] = value

            #print key, result[key]

        # compile authors list of dictionaries
        # we can have authors
        if result.has_key('author'):
            for each in result['author']:
                each = each.replace(' AND', ' and')
                authorlist.extend( each.split(' and') )
        # but for some bibref types we can have editors alternatively
        elif result.has_key('editor') and (type in ['book','proceedings']):
            result['editor_flag'] = True
            for each in result['editor']:
                each = each.replace(' AND', ' and')
                authorlist.extend( each.split(' and') )
        if result.has_key('authorURLs'):
            authorURLlist = result['authorURLs'].split('and ')

        if authorlist:
            alist = []
            authorlist = [x for x in authorlist if x]
            for author in authorlist:
                fname = mname = lname = ''
                parts = self.splitAuthor(author)
                if len(parts) == 1:
                    lname = parts[0].strip()
                else:
                    lname = parts[-1].strip()
                    fname = parts[0].strip()
                    if parts[1:-1]:
                        for part in parts[1:-1]:
                            mname = mname + part.strip()
                adict = {'firstname': fname,
                         'middlename': mname,
                         'lastname': lname}
                alist.append(adict)

        if authorURLlist and alist:
            index = 0
            for url in authorURLlist:
                alist[index]['homepage'] = url.strip()
                index += 1

        if authorlist:
            result['authors'] = alist

        # do some renaming and reformatting
        tmp = result.get('note')
        while tmp and tmp[-1] in ['}', ',', '\n', '\r']:
            tmp = tmp[:-1]
        if tmp:
            result['note'] = tmp
        result['publication_year'] = result.get('year', '')
        result['publication_month'] = result.get('month', '')
        result['publication_url'] = result.get('url', '')
        ## result['publication_title'] = result.get('title', '')
        tmp = result.get('title','')
        for car in ('\n', '\r', '\t'):
            tmp = tmp.replace(car, ' ')
        while '  ' in tmp:
            tmp = tmp.replace('  ', ' ')
        result['title'] = tmp

        # collect identifiers
        identifiers = list()
        for key in ('isbn', 'doi', 'asin', 'purl', 'urn', 'issn'):
            if key in result:
                identifiers.append({'label' : key.upper(), 'value': result[key]})
        if identifiers:
            result['identifiers'] = identifiers

        return result

    # the helper method's

    def splitAuthor(self, author=None):
        if not author: 
            return []
        #parts = author.replace('.', ' ').split(',',1)
        parts = author.split(',',1)
        if len(parts) == 1: 
            return parts[0].split()
        else:
            tmp = parts[1].split()
            tmp.append(parts[0])
            return tmp

    def splitMultiple(self, value):
        value = self.clean(value)
        result = list()
        for item in value.split(','):
            item = item.strip()
            if item:
                result.append(item)
        return result

    def clean(self, value):
        value = value.replace('{', '').replace('}', '').strip()
        if value and value[0] == '"' and len(value) > 1:
            value = value[1:-1]
        return value

    def cleanLine(self, value):
        return self.clean(value.rstrip().rstrip(',').rstrip())

    def group(self, p,n):
        """ Group a sequence p into a list of n tuples."""
        mlen, lft = divmod(len(p), n)
        if lft != 0: 
            mlen += 1

        # initialize a list of suitable length
        lst = [[None]*n for i in range(mlen)]

        # Loop over all items in the input sequence
        for i in range(len(p)):
            j,k = divmod(i,n)
            lst[j][k] = p[i]

        return map(tuple, lst)
