from gevent import Greenlet
import gevent.socket


def IOPassThrough(source, dest):
    return Greenlet(io_pass_through, source, dest)


def io_pass_through(source, dest):
    while True:
        gevent.socket.wait_read(source.fileno())
        msg = source.readline()

        if not msg:
            break

        dest.write(msg)
        dest.flush()
