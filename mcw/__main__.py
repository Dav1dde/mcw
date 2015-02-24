#!/usr/bin/env python2

from mcw.www import create_intstance, MinecraftAppMiddleware
from mcw.minecraft.server import Minecraft
from mcw.backup.rsync import RsyncBackup
from mcw.backup.dummy import DummyBackup
from mcw.config import ConfigFile

from gevent.wsgi import WSGIServer

import signal
import gevent
import os.path
import argparse


def server_from_config(config):
    return Minecraft(config.pop('path'), config.pop('jar'), **config)


def _argparse_filepath(path):
    if not os.path.exists(path) or not os.path.isfile(path):
        raise argparse.ArgumentError(
            'Invalid path for config, {0}'.format(path)
        )
    return path


def wait_or_kill(minecraft, timeout):
    try:
        minecraft.wait(timeout)
        return
    except gevent.subprocess.TimeoutExpired:
        minecraft._process.terminate()

    try:
        minecraft.wait(1)
    except gevent.subprocess.TimeoutExpired:
        minecraft._process.kill()


def register_signal_handler(minecraft, socketio=None):
    def handler(num, frame):
        if socketio is not None and socketio.server is not None:
            socketio.server.stop()

        if minecraft.is_running:
            minecraft._write('stop\n')

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main():
    parser = argparse.ArgumentParser('mcw')
    parser.add_argument(
        '--backup-delay', type=int, default=600
    )
    parser.add_argument(
        '--debug', action='store_true'
    )
    parser.add_argument(
        'config', type=_argparse_filepath,
        help='Path to configfile', metavar='FILE'
    )
    ns = parser.parse_args()

    config = ConfigFile(ns.config)

    minecraft = server_from_config(config.server)

    backup = DummyBackup()
    if config.backup.getboolean('enabled'):
        backup = RsyncBackup(
            minecraft, config.backup['path'],
            worldonly=config.backup.getboolean('worldonly', fallback=True),
            world=config.backup.get('world')
        )
        backup.start(ns.backup_delay)

    minecraft.start()
    if not config.webpanel.getboolean('enabled'):
        register_signal_handler(minecraft)
        wait_or_kill(minecraft, 10)
        # quit when the last backup is done
        while not backup.is_idle:
            gevent.sleep(0.5)
        return

    app, socketio, mw = create_intstance(
        minecraft, backup, config.webpanel['secret']
    )
    app.config.password = config.webpanel['password']
    app.debug = ns.debug

    register_signal_handler(minecraft, socketio)

    socketio.run(app, host=config.webpanel['host'],
                 port=int(config.webpanel['port']))
    wait_or_kill(minecraft, 10)


if __name__ == '__main__':
    main()
