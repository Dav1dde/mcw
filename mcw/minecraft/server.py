import gevent
import gevent.pool
import gevent.queue
import gevent.subprocess
import psutil

import re
import sys
import shlex
import signal
import os.path
from functools import partial
from datetime import datetime

from mcw.io import IOPassThrough, flush_fd
from mcw.signals import (
    on_starting, on_started, on_stopping, on_stopped,
    on_stdin_message, on_stdout_message, on_stderr_message
)
import mcw.minecraft.local
import mcw.minecraft.query

is_64bits = sys.maxsize > 2**32


_SERVER_STOP_RE = re.compile(
    r'^\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\]: Stopping the server$'
)
_SERVER_START_RE = re.compile(
    r'^\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\]: Done \(\d+[.,]\d+\w\)!'
    r' For help, type "help" or "\?"$'
)


class Minecraft(object):
    def __init__(self, path, jar, java='java',
                 minmem='512M', maxmem='1024M', args=''):
        self.path = path
        self.jar = jar
        self.java = java
        self.minmem = minmem
        self.maxmem = maxmem
        self.args = args

        self._server_properties = None
        self._process = None
        self._psutil_process = None
        self._pool = gevent.pool.Group()
        self._message_queue = gevent.queue.Queue()

        on_stdout_message.connect(self._on_stdout, sender=self)

    def _write(self, message):
        if self.is_running:
            self._process.stdin.write(message)
            self._process.stdin.flush()
            return True
        return False

    def _on_stdout(self, _, message):
        if _SERVER_START_RE.match(message):
            self._state = 'started'
            on_started.send(self)
        elif _SERVER_STOP_RE.match(message):
            self._state = 'stopping'
            on_stopping.send(self)

    @property
    def server_properties(self):
        if self._server_properties is None:
            self._server_properties = \
                mcw.minecraft.local.server_properties(self.path)

        return self._server_properties

    @property
    def ip(self):
        ip = self.server_properties['server-ip']
        return ip if ip else '127.0.0.1'

    @property
    def port(self):
        return self.server_properties['server-port']

    @property
    def info(self):
        if not self.state == 'started':
            return None
        return mcw.minecraft.query.get_info(self.ip, self.port)

    @property
    def process(self):
        return self._psutil_process

    @property
    def arguments(self):
        if self.args:
            return shlex.split(self.args)

        m = [
            '-server',
            '-Xms{}'.format(self.minmem),
            '-Xmx{}'.format(self.maxmem)
        ]

        if is_64bits:
            m.append('-d64')

        return m

    @property
    def is_running(self):
        return self._process is not None and self._process.poll() is None

    @property
    def state(self):
        return self._state

    def start(self):
        if self.is_running:
            raise ValueError("Server already running")

        cmd = self.arguments
        cmd.insert(0, self.java)
        cmd.extend(['-jar', self.jar, 'nogui'])

        # clear stdin, so process doesn't get leftover commands
        flush_fd(sys.stdin)
        self._process = gevent.subprocess.Popen(
            cmd, cwd=self.path, universal_newlines=True,
            stdin=gevent.subprocess.PIPE, stdout=gevent.subprocess.PIPE,
            stderr=gevent.subprocess.PIPE
        )
        self._psutil_process = psutil.Process(self._process.pid)
        self._state = 'starting'
        on_starting.send(self)

        def stop_event_g():
            self._process.wait()
            self._psutil_process = None
            self._state = 'stopped'
            on_stopped.send(self)
            self._pool.kill()
        self._pool.spawn(stop_event_g)

        def mkcb(signal):
            def callback(message):
                signal.send(self, message=message)
            return callback

        # forward stdin, stderr and stdout
        for src, dest, cb in [
            (sys.stdin, self._process.stdin, mkcb(on_stdin_message)),
            (self._process.stdout, sys.stdout, mkcb(on_stdout_message)),
            (self._process.stderr, sys.stderr, mkcb(on_stderr_message))
        ]:
            g = IOPassThrough(src, dest, cb)
            self._pool.add(g)
            g.start()

    def stop(self):
        if not self.state == 'started':
            if self.state == 'starting':
                raise ValueError('Minecraft server ist starting')
            raise ValueError('Minecraft server is not started')

        self._write('stop\n')

    def wait(self, timeout=None):
        self._process.wait(timeout=timeout)


