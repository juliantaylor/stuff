stuff
=====

Random stuff

adt-runscript.py
----------------

Very basic Debian autopkgtest execution script creator.
Given a dsc (and optional a changes file) it produces a script which installs
the dependencies and runs the registered tests.
The script is intended to be executed in a isolated environment, e.g.
via `pbuilder --execute`.

Warning:
intended for personal use, behavior and interface may change at any time.

##### Usage:

```bash
$ adt-runscript.py python-tornado_3.1.1-1.dsc python-tornado_3.1.1-1_amd64.changes
dpkg-source: warning: extracting unsigned source package (/var/cache/pbuilder/result/python-tornado_3.1.1-1.dsc)
dpkg-source: info: extracting python-tornado in python-tornado-3.1.1
dpkg-source: info: unpacking python-tornado_3.1.1.orig.tar.gz
dpkg-source: info: unpacking python-tornado_3.1.1-1.debian.tar.gz
dpkg-source: info: applying ignore-ca-certificates.patch
dpkg-source: info: applying certs-path.patch
dpkg-source: info: applying ignoreuserwarning.patch
python2 python-tornado []
python3 python3-tornado []
to run the tests execute:
sudo DIST=precise cowbuilder --execute "/tmp/sadttmp-python-tornado-precise/runscript.sh" --bindmount "/tmp/sadttmp-python-tornado-precise" --logfile "/tmp/python-tornado_3.1.1-1.log"
```

##### Issues:

 * No support for test restrictions yet.
 * Fails on signed changes files.
