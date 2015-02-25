from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import os.path
import shelve
import glob
import os

from werkzeug import secure_filename
import gevent.subprocess
import gevent.pool
import gevent

from mcw.signals import on_backup_started, on_backup_stopped, on_backup_deleted
from mcw.utils.store import JsonStore


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

        self.metadata = JsonStore(os.path.join(path, 'metadata.json'))

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
                if backup.name in self.metadata:
                    label = self.metadata[backup.name]

                ret[type].append({
                    'name': backup.name, 'date': backup.date,
                    'size': backup.size, 'label': label
                })
        return ret

    def get_label(self, name):
        if name in self.metadata:
            return self.metadata[name]
        return None

    def delete_backup(self, name):
        if not name.endswith(self.EXTENSION):
            raise ValueError('invalid name')

        names = os.listdir(self.path)
        if name not in names:
            raise KeyError('backup does not exist')

        os.remove(os.path.join(self.path, name))
        on_backup_deleted.send(self, name=name)

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
        time, name = self.create_backup('user', label)

    def create_backup(self, type, label=None):
        raise NotImplementedError()

    def remove_old_backups(self, job, past):
        to_delete = past[:max(0, len(past)-job.num)]

        for dt in to_delete:
            name = '{0}.{1}'.format(
                self.get_backup_name(job.name, dt), self.EXTENSION
            )
            os.remove(os.path.join(self.path, name))
