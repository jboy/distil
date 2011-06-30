README:
------

1. There are 4 Python library dependencies, listed in "DEPS.txt".

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

