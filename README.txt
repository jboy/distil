README:
------

1. There are 5 Python library dependencies, listed in "DEPS.txt".

2. You need a per-installation config file named ".distil.cfg" in
either your home directory or the directory from which you run Distil;
see "example.distil.cfg" for details.  (You can pretty much just copy
this file to be "~/.distil.cfg" and edit the values as appropriate.)

3. A "doclib" is the outermost directory (within an existing Git repo)
within which you want Distil to store everything.  So for example, in
my own installation, I have a "Thesis" Git repo in my home directory,
and a "doclib" subdirectory in that repo to contain the papers, bibs,
etc... everything managed by Distil.  As a result, my config variable
"doclib_base_abspath" is set to "~/Thesis/doclib".

4. There are convenience shell scripts in the "bin" directory; you
can copy these into your PATH and edit the DISTIL shell variable in
each script to point to the Distil code installation.

5. To run the webserver, it's just "python webserver.py", then direct
your browser to http://localhost:8888/

6. To import BibTeX bib-files (with optional PDFs and abstracts), use
"python import_bib_command.py" or the equivalent shell-script wrapper
"bin/distil-import-bib".  The "--help" command-line flag will print a
brief usage message.  Note that the bib-importer currently processes
only one bib-entry per invocation, and so will expect each BibTeX file
to contain only a single bib-entry.  Note also that when the specified
files are imported, they will be moved rather than copied.

7. The currently-supported wiki markup is a (slightly-extended) subset
of the Trac wiki syntax.  In particular:
 * = First-level Heading =
 * == Second-level Heading ==
 * === Third-level Heading ===
 * A paragraph is a sequence of lines of text, ended by an empty line
 * A bullet-point is a space followed by an asterisk (" *")
   * Indent the space-asterisk by 2 extra spaces for a sub-point
     * And so on...
 * A numbered item is a space followed by a digit and a period (" 1.")
   1. Similarly with the 2 extra spaces for a sub-item
 * A wiki word is created using [square brackets]
   * Wiki words are case-insensitive (they will be converted to lower)
   * Spaces are allowed (they will be converted to hyphens)
 * Cite a paper in Distil using [cite:the-cite-key-of-the-paper]
 * **bold text** (currently must be completely on a single line, alas)
 * //italicised text// (again, currently must be on a single line)
 * +++highlighted text+++ (on a single line)

8. For more documentation about Distil (including screenshots and
presentation slides that provide a higher-level overview), take a look
at http://github.com/jboy/distil-extra-doc
