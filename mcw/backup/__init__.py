from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import os.path
import shelve
import glob
import os

import gevent.subprocess
import gevent.pool
import gevent


BackupJob = namedtuple('BackupJob', ['name', 'delta', 'num'])
BackupFile = namedtuple('BackupFile', ['name', 'date', 'size'])


class Backup(object):
    EXTENSION = None

    FORMAT = '%Y-%m-%dT%H:%M:%S'
    BACKUPS = [
        BackupJob('hourly', timedelta(hours=1), 6),
        BackupJob('daily', timedelta(days=1), 7),
        BackupJob('weekly', timedelta(weeks=1), 4),
        BackupJob('monthly', timedelta(weeks=4), 2)
    ]

    def __init__(self, minecraft, path, worldonly=True, world=None):
        self.minecraft = minecraft
        self.path = path
        self.worldonly = worldonly
        self.world = world
        if world is None or world.strip().lower() == '*guess*':
            self.world = self.minecraft.server_properties['level-name']
        self.source = self.minecraft.path

        if not os.path.exists(self.source):
            raise ValueError('Source folder for backups does not exist')

        if not os.path.exists(self.path):
            raise ValueError('Destination folder for backups does not exist')

        self._last = os.path.join(self.path, 'server')
        if not os.path.exists(self._last):
            os.makedirs(self._last)

        self.metadata = shelve.open(os.path.join(path, 'metadata'))

        self._pool = gevent.pool.Pool()
        self._in_backup = False
        self._processes = list()

    @classmethod
    def collect_backups(cls, path):
        files = os.path.join(path, 'backup-*-*.{0}'.format(cls.EXTENSION))

        backups = defaultdict(list)
        for backup in sorted(glob.glob(files)):
            size = os.path.getsize(backup)
            name = os.path.split(backup)[1]
            try:
                _, type, date = name.split('-', 2)
                date = date.split('.', 1)[0]
                date = datetime.strptime(date, cls.FORMAT)
            except (ValueError, IndexError):
                continue
            backups[type].append(BackupFile(name, date, size))

        return backups

    @classmethod
    def get_backup_name(cls, name, dt=None):
        if dt is None:
            dt = datetime.now()

        return 'backup-{}-{}'.format(name, dt.strftime(cls.FORMAT))

    @property
    def is_idle(self):
        # all unfinished processes
        self._processes = [p for p in self._processes if p.poll() is None]
        # not _in_backup and no process running
        return not self._in_backup and len(self._processes) == 0

    def get_backups(self):
        ret = defaultdict(list)
        for type, backups in self.collect_backups(self.path).items():
            for backup in backups:
                label = type
                if self.metadata.has_key(backup.name.encode('utf-8')):
                    label = self.metadata[backup.name.encode('utf-8')]

                ret[type].append({
                    'date': backup.date, 'size': backup.size, 'label': label
                })

        return ret

    def start(self, delay=600):
        def exc(gr):
            self._in_backup = False

        g = gevent.spawn_later(delay, self.run)
        g.link_exception(exc)
        self._pool.add(g)

    def run(self):
        self._in_backup = True

        backups = self.collect_backups(self.path)
        for job in self.BACKUPS:
            past = [b.date for b in backups.get(job.name, [])]
            self.create_backup_if_required(job, past)

        self._in_backup = False

        def exc(gr):
            self._in_backup = False

        g = gevent.spawn_later(3600, self.run)
        g.link_exception(exc)
        self._pool.add(g)

    def create_backup_if_required(self, job, past, force=False):
        if not self.minecraft.is_running and not force:
            return

        now = datetime.now()
        # past has to be sorted
        last = past[-1] if past else datetime.min

        if now - last > job.delta or force:
            # we make a new backup, add it to the past list
            past.append(self.create_backup(job.name)[0])
            # only a maximum number of backups allowed, remove
            # too old backups
            self.remove_old_backups(job, past)

    def create_user_backup(self, label):
        time, name = self.create_backup('user', self._user)
        self.metadata[name.encode('utf-8')] = label

    def create_backup(self, name):
        raise NotImplementedError()

    def remove_old_backups(self, job, past):
        to_delete = past[:max(0, len(past)-job.num)]

        for dt in to_delete:
            name = '{0}.{1}'.format(self.get_backup_name(job.name, dt), self.EXTENSION)
            os.remove(os.path.join(self._scheduled, name))
