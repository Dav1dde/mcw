import gevent
import gevent.pool
import gevent.queue
import gevent.subprocess

import sys
import shlex
import signal
import os.path
from functools import partial
from datetime import datetime

from mcw.io import IOPassThrough
from mcw.signals import (
    on_started, on_stopped,
    on_stdin_message, on_stdout_message, on_stderr_message
)


is_64bits = sys.maxsize > 2**32


class Minecraft(object):
    def __init__(self, config):
        self.config = config

        self._process = None
        self._pool = gevent.pool.Group()
        self._message_queue = gevent.queue.Queue()

    def _write(self, msg):
        if self.is_running:
            self._process.stdin.write(msg)
            self._process.stdin.flush()
            return True
        return False

    @property
    def arguments(self):
        m = [
            '-server',
            '-Xms{}'.format(self.config['minmem']),
            '-Xmx{}'.format(self.config['maxmem'])
        ]

        if is_64bits:
            m.append('-d64')

        m.extend(shlex.split(self.config.get('args', '')))

        return m

    @property
    def is_running(self):
        return self._process is not None and self._process.poll() is None

    def start(self):
        if self.is_running:
            raise ValueError("Server already running")

        cmd = self.arguments
        cmd.insert(0, self.config['java'])
        cmd.extend(['-jar', self.config['jar'], 'nogui'])

        self._process = gevent.subprocess.Popen(
            cmd, cwd=self.config.get('path'), universal_newlines=True,
            stdin=gevent.subprocess.PIPE, stdout=gevent.subprocess.PIPE,
            stderr=gevent.subprocess.PIPE
        )

        on_started.send(self)

        def stop_event_g():
            self._process.wait()
            on_stopped.send(self)
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
        self._write('stop\n')

    def wait(self):
        self._process.wait()


class Spigot(Minecraft):
    @property
    def arguments(self):
        m = Minecraft.arguments.fget(self)
        m.append('-XX:MaxPermSize=128M')
        return m


class FTB(Minecraft):
    @property
    def arguments(self):
        m = Minecraft.arguments.fget(self)
        m.extend([
            '-XX:PermSize=256m', '-XX:+UseParNewGC',
            '-XX:+CMSIncrementalPacing', '-XX:+CMSClassUnloadingEnabled',
            '-XX:ParallelGCThreads=2', '-XX:MinHeapFreeRatio=5',
            '-XX:MaxHeapFreeRatio=10'
        ])
        return m


