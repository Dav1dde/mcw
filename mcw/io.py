from gevent import Greenlet
import gevent.socket

import termios


def IOPassThrough(source, dest, callback=None):
    return Greenlet(io_pass_through, source, dest, callback)


def io_pass_through(source, dest, callback=None):
    while True:
        gevent.socket.wait_read(source.fileno())
        msg = source.readline()

        if not msg:
            break

        dest.write(msg)
        dest.flush()

        if callback is not None:
            callback(msg)


def flush_fd(fd):
    termios.tcflush(fd, termios.TCIOFLUSH)
