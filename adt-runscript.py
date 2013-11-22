#!/usr/bin/env python
"""
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions: 

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software. 

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Copyright 2013 Julian Taylor
"""

import subprocess as sp
from debian import deb822
from debian import debfile
import os
import sys
import tempfile

if len(sys.argv) < 2:
    print "usage: adt-runscript.py <dsc> [changes]"
    print "Prepare script to run autopkgtests in pbuilder via --execute\n"
    print "if provided with only a dsc it will download the dependencies " \
          "from the archive."
    print "if provided with a dsc and a changes file it will use the local "\
          "packages from the changes file."
    sys.exit(0)


class Test:
    def __init__(self, name):
        self.name = name
        self.depends = []
        self.restrictions = []
    def parse_depends(self, d):
        self.depends = set([x.split()[0] for x in d.split(",")  if "libc" not in x])


target = "saucy"
dsc = os.path.abspath(sys.argv[1])
loc_pkg_paths = set()
loc_pkg_names = set()
if len(sys.argv) > 2:
    changes = os.path.abspath(sys.argv[2])
    c = deb822.Changes.iter_paragraphs(open(changes)).next()
    target = c["Distribution"]
    loc_pkg_paths = set([os.path.join(os.path.dirname(changes), x["name"])
                    for x in c["Checksums-Sha1"] if x["name"].endswith("deb")])
    loc_pkg_names = set([os.path.basename(pkg).split("_")[0] for pkg in loc_pkg_paths])

# gather dependencies of the local packages
loc_pkg_deps = dict()
for dp in loc_pkg_paths:
    dc = dict(debfile.DebFile(dp).debcontrol().items())
    dn = dc["Package"]
    if "Depends" in dc:
        loc_pkg_deps[dn] = set([pkg.split()[0]
                           for pkg in dc["Depends"].split(",")]) & loc_pkg_names


# extract source package
tmp = "/tmp/sadttmp-%s-%s" % (os.path.basename(dsc).split("_")[0], target) #tempfile.mkdtemp()
try:
    os.makedirs(tmp)
except OSError:
    pass
os.chdir(tmp)
sp.call(["dpkg-source", "-x", dsc])
for d in os.listdir("."):
    if os.path.isdir(d) and d.startswith(os.path.basename(dsc).split("_")[0]):
        pkgdir = d
        break
logfile = os.path.splitext(os.path.basename(dsc))[0] + ".log"

with_exp = "-t experimental" if target == "experimental" else ""

# gather tests
tests = []
for f in deb822.Packages.iter_paragraphs(open(os.path.join(pkgdir, "debian/tests/control"))):
    for k, v in f.iteritems():
        if k == "Tests":
            tests.append(Test(v))
        elif k == "Depends":
            if v == "@":
                tests[-1].depends = list(loc_pkg_names)
            else:
                tests[-1].parse_depends(v)
        elif k == "Restrictions":
            if v.lower() in ("breaks-testbed", "rw-build-tree"):
                raise ValueError("Restriction %s not supported" % v)
            tests[-1].restrictions.append(v)

# no Depends means implicit @
for t in tests:
    if not t.depends:
        t.depends = list(loc_pkg_names)

# copy the local pacakges
for pkg in loc_pkg_paths:
    import shutil
    shutil.copy(pkg, ".")
loc_pkg_paths = [os.path.basename(pkg) for pkg in loc_pkg_paths]


# prepare the script
with open("runscript.sh", "w") as f:
    f.write("#!/bin/bash\n")
    f.write("set -xe\n")
    # same id as pbuilder for firewalling
    f.write("useradd -u 1234 adttesting\n")
    f.write("cd %s\n" % os.path.join(tmp, pkgdir))
    for t in tests:
        aptdep = " ".join(t.depends - loc_pkg_names)

        # resolve local dependencies, only one level, but should be enough for most packages
        dpkgdep = loc_pkg_names & t.depends
        for d in list(dpkgdep):
            print t.name, d, list(loc_pkg_deps[d])
            dpkgdep = dpkgdep.union(loc_pkg_deps[d])
        if dpkgdep:
            dpkgdeppath = [os.path.join(tmp, d) for d in loc_pkg_paths if d.split("_")[0] in dpkgdep]
            f.write("dpkg -i %s || true\n" % " ".join(dpkgdeppath))
            f.write("apt-get install -f -y --force-yes %s\n" % with_exp)
        all_installed = " ".join(t.depends | dpkgdep)

        asuser = "" if "needs-root" in t.restrictions else "su adttesting -c"

        f.write("""\
apt-get install -y --force-yes {aptdep}
rm -rf /tmp/sadt
mkdir -p /tmp/sadt
chown adttesting /tmp/sadt
set +e
TMPDIR=/tmp/sadt ADTTMP=/tmp/sadt {asuser} debian/tests/{testname} 2> errlog
ret=$?
set -e
if [ ! $(cat errlog | wc -l) -eq 0 ]; then
  echo 'STDERR LOG:';
  cat errlog;
  echo STDERR FAILURE;
  exit 1;
fi
if [ $ret -ne 0 ]; then
  echo FAILURE $ret;
  exit $ret;
fi
""".format(aptdep=aptdep, testname=t.name, asuser=asuser))

        if t != tests[-1] and "--fast" not in sys.argv:
            f.write("apt-get autoremove -y --force-yes --purge %s\n" % all_installed)
    f.write("echo SUCCESS\n")

print 'to run the tests execute:'
print 'sudo DIST=%s cowbuilder --execute "%s/runscript.sh" --bindmount "%s" --logfile "/tmp/%s"' % (target, tmp, tmp, logfile)

