GNU gettext / libintl
=====================

The macOS distribution of SimpleOB contains the GNU libintl shared
library from GNU gettext version 1.0:

- libintl.8.dylib

The library is used by the Python 3.12 runtime included with SimpleOB.

License
-------

GNU libintl is free software licensed under the GNU Lesser General
Public License as published by the Free Software Foundation, either
version 2.1 of the License, or (at your option) any later version
(LGPL-2.1-or-later).

The copyright notice in the libintl.h file supplied with GNU gettext
1.0 states:

Copyright (C) 1995-2026 Free Software Foundation, Inc.

A copy of the GNU Lesser General Public License version 2.1 is included
in this directory as:

LGPL-2.1.txt

Corresponding source
--------------------

The upstream source archive corresponding to this version is:

gettext-1.0.tar.gz

SHA-256:

85d99b79c981a404874c02e0342176cf75c7698e2b51fe41031cf6526d974f1a

The source archive is published by the GNU Project.

Information about the SimpleOB-controlled download location for the
corresponding source archive will be provided with the SimpleOB
distribution or on the SimpleOB distribution website.

Library replacement
-------------------

libintl.8.dylib is distributed as a separate dynamically linked library
inside the SimpleOB application bundle.

Users may replace the LGPL-covered library with a compatible modified
version for their own use as permitted by the LGPL.

On macOS, replacing a library inside the application bundle may
invalidate the existing code signature. The modified application bundle
can be signed locally with an ad-hoc signature using Apple's codesign
tool.

An Apple Developer ID certificate is not required for an ad-hoc
signature.

Depending on the macOS security configuration and how the application
was obtained, macOS may require the user to explicitly approve opening
the modified application.

It is not necessary to disable Gatekeeper globally.

SimpleOB application code
-------------------------

The license applicable to GNU libintl does not change the license
applicable to the separately developed SimpleOB application code.

See LGPL-2.1.txt for the complete GNU Lesser General Public License
version 2.1 terms.
