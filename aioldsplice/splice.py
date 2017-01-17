# based heavily on work from https://gist.github.com/NicolasT/4519146

from __future__ import absolute_import, division, print_function

import os
import os.path

import ctypes
import ctypes.util


def make_splice():
    '''Set up a splice(2) wrapper'''

    # Load libc
    libc_name = ctypes.util.find_library('c')
    libc = ctypes.CDLL(libc_name, use_errno=True)

    # Get a handle to the 'splice' call
    c_splice = libc.splice

    # These should match for x86_64, might need some tweaking for other
    # platforms...
    c_loff_t = ctypes.c_uint64
    c_loff_t_p = ctypes.POINTER(c_loff_t)

    # ssize_t splice(int fd_in, loff_t *off_in, int fd_out,
    #     loff_t *off_out, size_t len, unsigned int flags)
    c_splice.argtypes = [
        ctypes.c_int, c_loff_t_p,
        ctypes.c_int, c_loff_t_p,
        ctypes.c_size_t,
        ctypes.c_uint
    ]
    c_splice.restype = ctypes.c_ssize_t

    # Clean-up closure names. Yup, useless nit-picking.
    del libc
    del libc_name
    del c_loff_t_p

    # pylint: disable-msg=W0621,R0913
    def splice(fd_in, off_in, fd_out, off_out, len_, flags):
        '''Wrapper for splice(2)
        See the syscall documentation ('man 2 splice') for more information
        about the arguments and return value.
        `off_in` and `off_out` can be `None`, which is equivalent to `NULL`.
        If the call to `splice` fails (i.e. returns -1), an `OSError` is raised
        with the appropriate `errno`, unless the error is `EINTR`, which results
        in the call to be retried.
        '''

        c_off_in = \
            ctypes.byref(c_loff_t(off_in)) if off_in is not None else None
        c_off_out = \
            ctypes.byref(c_loff_t(off_out)) if off_out is not None else None

        res = c_splice(fd_in, c_off_in, fd_out, c_off_out, len_, flags)

        if res == -1:
            errno_ = ctypes.get_errno()

            raise IOError(errno_, os.strerror(errno_))

        return res

    return splice


# Build and export wrapper
splice = make_splice()
del make_splice


# From bits/fcntl.h
# Values for 'flags', can be OR'ed together
SPLICE_F_MOVE = 1
SPLICE_F_NONBLOCK = 2
SPLICE_F_MORE = 4
SPLICE_F_GIFT = 8
