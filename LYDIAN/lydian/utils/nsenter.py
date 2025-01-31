#!/usr/bin/env python
# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
Utilties to temporarily enter linux namespaces.

Demo:

$ ip netns add testns
$ ip link add veth0 type veth peer name veth1
$ ip link set veth1 netns testns
$ ip link list | grep veth
315: veth0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
$ ip netns exec testns ip link list | grep veth
314: veth1: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
$ python
...
>>> from lydian.utils.nsenter import *
>>> print(os.popen('ip link list | grep veth').read().strip())
315: veth0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
>>> with namespace('/var/run/netns/testns', 'net'):
...     print(os.popen('ip link list | grep veth').read().strip())
...
314: veth1: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
>>>
>>> print(os.popen('ip link list | grep veth').read().strip())
315: veth0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
>>>
"""

import contextlib
import ctypes.util
import logging
import os
import errno

logger = logging.getLogger(__name__)
LIBC = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
VALID_NAMESPACES = frozenset(['ipc', 'mnt', 'net', 'pid', 'user', 'uts'])
OPENED_FDS = {}


def setns(fd):
    """See http://man7.org/linux/man-pages/man2/setns.2.html"""
    if LIBC.setns(fd, 0) == -1:
        err = ctypes.get_errno()
        raise OSError(err, errno.errorcode[err])


@contextlib.contextmanager
def fdopen(path):
    """
    Open a read-only fd to <path> if not present in OPENED_FDS.
    If present, directly yields the file descriptor.
    """
    global OPENED_FDS
    if path in OPENED_FDS:
        fd = OPENED_FDS[path]
        yield fd
    else:
        fd = os.open(path, os.O_RDONLY)
        OPENED_FDS[path] = fd
        yield fd


def fdcloseall():
    """
    Closes all the file descriptors opened and recorded in OPENED_FDS.
    """
    global OPENED_FDS
    for fd in OPENED_FDS.values():
        os.close(fd)
    OPENED_FDS = {}


@contextlib.contextmanager
def namespace(nspath, nstype, verbose=False):
    """Enter the provided namespace"""
    if nstype not in VALID_NAMESPACES:
        raise ValueError("invalid namespace type %r" % nstype)

    with fdopen("/proc/self/ns/%s" % nstype) as original_ns:
        with fdopen(nspath) as new_ns:
            if verbose:
                logger.debug("Entering %s namespace %s", nstype,
                             nspath)
            setns(new_ns)
        try:
            yield
        finally:
            if verbose:
                logger.debug("Leaving %s namespace %s", nstype, nspath)
            setns(original_ns)


Namespace = namespace
