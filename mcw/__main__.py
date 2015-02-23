#!/usr/bin/env python2

from mcw.www import create_intstance, MinecraftAppMiddleware
from mcw.minecraft.server import Minecraft, Spigot, FTB
from mcw.backup.rsync import RsyncBackup
from mcw.backup.dummy import DummyBackup
from mcw.config import ConfigFile

from gevent.wsgi import WSGIServer

import signal
import gevent
import os.path
import argparse


SERVER_TYPES = {
    'minecraft': Minecraft,
    'spigot': Spigot,
    'ftb': FTB
}


def server_from_config(config):
    config = dict(config)
    Cls = SERVER_TYPES[config.pop('type').strip().lower()]

    return Cls(config.pop('path'), config.pop('jar'), **config)


def _argparse_filepath(path):
    if not os.path.exists(path) or not os.path.isfile(path):
        raise argparse.ArgumentError(
            'Invalid path for config, {0}'.format(path)
        )
    return path


def register_signal_handler(minecraft):
    def handler(num, frame):
        if minecraft.is_running:
            minecraft.stop()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main():
    parser = argparse.ArgumentParser('mcw')
    parser.add_argument(
        '--backup-delay', type=int, default=600
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
        minecraft.wait()
        # quit when the last backup is done
        while not backup.is_idle:
            gevent.sleep(0.5)
        return

    app, socketio = create_intstance(config.webpanel['secret'])
    app.config.password = config.webpanel['password']

    mw = MinecraftAppMiddleware(minecraft, app, socketio)

    socketio.run(app, host=config.webpanel['host'],
                 port=int(config.webpanel['port']))


if __name__ == '__main__':
    main()
