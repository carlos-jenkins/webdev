======================
Development Web Server
======================

About
=====

This is a small web server for development or sharing purposes.
It allows to serve through HTTP any directory in your machine.
It is based on Python famous `SimpleHTTPServer` and it only depends on a
Python 2.7 interpreter and the standard library.

In contrast to ``SimpleHTTPServer`` this development web server:

- Allows the serving folder can be passed as the first positional argument.
  Defaults to current directory.
- Will respond with 404 if the serving folder is removed; instead of crashing.
- Will return back to normal operation if the folder is recreated.
  Very useful with build systems that perform clean actions.
- Bind IP can be specified in case security is a must while developing.

As with ``SimpleHTTPServer`` this web server can:

- Specify binding port.
- List directories.
- Serve ``index.html`` or ``index.html`` automatically as the directory entry.


Installation
============

::

   pip install webdev


Usage
=====

::

   $ webdev --help
   usage: webdev [-h] [-v] [--version] [-i IP] [-p PORT] [-f] [-r RANGE] [-u]
                 [path]

   Development Web Server

   positional arguments:
     path                  Path to serve. Default: Current directory.

   optional arguments:
     -h, --help            show this help message and exit
     -v, --verbose         Increase verbosity level
     --version             show program's version number and exit
     -i IP, --ip IP        IP to bind to. Default: 0.0.0.0
     -p PORT, --port PORT  Port to listen to. Default: 8080.
     -f, --force-port      Force the use of the given port.
     -r RANGE, --range RANGE
                           Number of ports to try from the base port
     -u, --future          Ignore if the folder to server doesn't exists yet


Changelog
=========

1.1.0
-----

**New**

- Added support for Python 3 (issue #5).
- Added support for incremental automatic port selection (issue #2).
- Added the ``--future`` flag that allows the webserver to serve a non-existent
  folder, assuming it will be created in the future (issue #3).

**Changed**

- Ctrl+C is now handled (issue #4).


1.0.0
-----

- Initial release.


License
=======

::

   Copyright (C) 2015-2016 Carlos Jenkins <carlos@jenkins.co.cr>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing,
   software distributed under the License is distributed on an
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
   KIND, either express or implied.  See the License for the
   specific language governing permissions and limitations
   under the License.
