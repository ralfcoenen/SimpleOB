Qt / PySide6 / Shiboken6
========================

SimpleOB uses Qt, PySide6 and Shiboken6 version 6.11.2.

The macOS distribution of SimpleOB contains the following Qt frameworks:

- QtCore
- QtDBus
- QtGui
- QtNetwork
- QtSvg
- QtWidgets

It also contains the PySide6 and Shiboken6 runtime components required
to use these Qt libraries from Python.

SimpleOB uses these components under the terms of the GNU Lesser General
Public License version 3 (LGPLv3).

SimpleOB itself is a separate application and is not licensed under the
LGPL or GPL merely because it uses these dynamically linked libraries.

Copies of the relevant original license texts are included in this
directory:

- LGPL-3.0.txt
- GPL-2.0.txt
- GPL-3.0.txt

Corresponding source code
-------------------------

The source archives corresponding to the Qt / PySide6 / Shiboken6
version distributed with this version of SimpleOB are:

qtbase-everywhere-src-6.11.2.tar.xz
SHA-256:
5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22

qtsvg-everywhere-src-6.11.2.tar.xz
SHA-256:
d594337feca84c26fb67fe87b85e6a5c12fda404b611d905f9d138210c311876

pyside-setup-everywhere-src-6.11.2.zip
SHA-256:
c0fdd62b91a1d36d5ee2e1fb71050a32fbc93fcdeef0fdcb41d29afaaf00d9b5

Information about obtaining the corresponding source code and about
replacing the LGPL-covered libraries is provided in
SOURCE_AND_RELINKING.txt.
