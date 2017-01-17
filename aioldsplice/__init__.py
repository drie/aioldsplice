#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function
from . import splice
import fcntl
import os
import asyncio
import logging

logger = logging.getLogger('aioldsplice')


async def proxy(l_conn, r_conn,
                chunksize=64 * 1024 * 1024,
                splice_flags=splice.SPLICE_F_MOVE | splice.SPLICE_F_NONBLOCK,
                _loop=None):
    loop = _loop if _loop is not None else asyncio.get_event_loop()
    l_read, r_write = os.pipe()
    r_read, l_write = os.pipe()
    _set_nonblock(l_read)
    _set_nonblock(r_write)
    _set_nonblock(r_read)
    _set_nonblock(l_write)
    logger.debug("proxy {} -> {} -> {} -> {} and {} -> {} -> {} -> {}".format(
        r_conn.fileno(), r_write, l_read, l_conn.fileno(),
        l_conn.fileno(), l_write, r_read, r_conn.fileno()))

    async def proxy_i(r_conn, w_conn):
        while True:
            try:
                await reader_ready(r_conn, _loop=loop)
            except asyncio.CancelledError:
                logger.debug("{} to {} cancelled, returning".format(r_conn, w_conn))
                return
            try:
                nbytes = splice.splice(r_conn, None, w_conn, None, chunksize, splice_flags)
            except IOError as e:
                if e.errno == 11:
                    logger.warning("{} waiting on write...".format(w_conn))
                    await asyncio.wait_for(writer_ready(w_conn, _loop=loop), 2.5)
                    continue
                raise
            if not nbytes:
                logger.debug("no bytes on the {} to {} path".format(r_conn, w_conn))
                return

    done, pending = await asyncio.wait([
        proxy_i(r_conn.fileno(), r_write),
        proxy_i(l_read, l_conn.fileno()),
        proxy_i(l_conn.fileno(), l_write),
        proxy_i(r_read, r_conn.fileno())
    ], return_when=asyncio.FIRST_COMPLETED)
    exception = done.pop().exception()
    for p in pending:
        p.cancel()
    done, pending = await asyncio.wait(pending)
    os.close(l_read)
    os.close(l_write)
    os.close(r_read)
    os.close(r_write)
    if exception:
        raise exception


def reader_ready(*args, **kwargs):
    return _ready('reader', *args, **kwargs)


def writer_ready(*args, **kwargs):
    return _ready('writer', *args, **kwargs)


def _ready(type, sock, _loop=None):
    f = asyncio.Future()
    loop = _loop if _loop is not None else asyncio.get_event_loop()

    def ready():
        getattr(loop, "remove_{}".format(type))(sock)
        if not f.cancelled():
            f.set_result(sock)

    getattr(loop, "add_{}".format(type))(sock, ready)
    return f


def _set_nonblock(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    flags |= os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)
