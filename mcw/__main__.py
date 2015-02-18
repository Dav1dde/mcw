#!/usr/bin/env python2

from mcw.minecraft import Minecraft, Spigot, FTB
from mcw.backup import RsyncBackup

import signal
import gevent


_REQUIRED_KEYS = (
    'type', 'java', 'jar', 'minmem', 'maxmem', 'path'
)


def register_signal_handler(minecraft):
    def handler(num, frame):
        if minecraft.is_running:
            minecraft.stop()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main():
    import configparser
    import argparse

    parser = argparse.ArgumentParser('mcw')
    parser.add_argument(
        '--backup-delay', type=int, default=600
    )
    parser.add_argument(
        'config', type=argparse.FileType('r'), help='Path to configfile'
    )
    parser.add_argument(
        'name', help='Config section for this server'
    )
    ns = parser.parse_args()

    config = configparser.ConfigParser()
    config.read_file(ns.config)
    config = config[ns.name]

    cls = {
        'minecraft': Minecraft,
        'spigot': Spigot,
        'ftb': FTB
    }[config['type'].strip().lower()]

    minecraft = cls(config)
    backup = RsyncBackup(minecraft, config['path'], config['backup'])
    backup.start(ns.backup_delay)

    register_signal_handler(minecraft)

    minecraft.start()
    minecraft.wait()
    # quit when the last backup is done
    while not backup.is_idle:
        gevent.sleep(0.5)


if __name__ == '__main__':
    main()