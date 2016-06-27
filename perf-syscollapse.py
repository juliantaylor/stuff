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

Copyright 2016 Julian Taylor
"""

import sys
import subprocess as sp
supported = ('syscalls:sys_enter_read', 'syscalls:sys_enter_write')

if len(sys.argv) != 2:
    print >> sys.stderr, 'collapse perf stacks to format suitable for flamegraph'
    print >> sys.stderr
    print >> sys.stderr, 'Usage: perf script | %s function' % sys.argv[0]
    print >> sys.stderr, 'Input perf script of perf record --call-graph dwarf -e function'
    print >> sys.stderr, 'function must be one of %r' % (supported,)
    sys.exit(0)

function = sys.argv[1]
if function not in supported:
    print >> sys.stderr, 'function must be one of %r' % (supported,)
    sys.exit(0)


class Trace:
    def __init__(self):
        self.bt = []

def parse_data(fun, data):
    if fun in supported:
        fd, fdval, buf, bufval, count, countval = rest.split()
        return {'fd': int(fdval.rstrip(','), 16), 'buf': int(bufval.rstrip(','), 16), 'count': int(countval.rstrip(','), 16)}

def demangle(s):
    if isinstance(s, basestring):
        p = sp.Popen(['c++filt', s], stdout=sp.PIPE)
        return p.communicate(s)[0]
    else:
        p = sp.Popen(['c++filt'] + list(s), stdout=sp.PIPE)
        return p.communicate(s)[0].splitlines()


jtraces = dict()
trace = None
for l in sys.stdin:
    if not l.strip():
        key = tuple(trace.bt)
        if key in jtraces:
            jtraces[key].data['count'] += trace.data['count']
        else:
            fun = demangle(x[0] for x in trace.bt)
            trace.bt = [' '.join(y) for y in zip(fun, (x[1] for x in trace.bt))]
            jtraces[key] = trace
        trace = None
        continue
    if trace is None:
        trace = Trace()
        trace.name, pid, trace.x, trace.time, fun, rest = l.split(None, 5)
        trace.pid = int(pid)
        trace.fun = fun[:-1]
        trace.data = parse_data(trace.fun, rest)
    else:
        # addr2line could be used to get line number in function
        addr, fun, rest = l.split(None, 2)
        trace.bt.append((fun, addr))


for t in jtraces.values():
    if t.fun == function:
        print (';'.join(t.bt) + '; %d' % t.data['count'])
