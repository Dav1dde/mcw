from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import os.path
import glob
import os

from gevent import subprocess
import gevent.pool
import gevent


BackupJob = namedtuple('BackupJob', ['name', 'delta', 'num'])

ZERO_TIME = datetime(0, 0, 0)


class RsyncBackup(object):
    FORMAT = '%Y-%m-%dT%H:%M:%S'
    BACKUPS = [
        BackupJob('hourly', timedelta(hours=1), 6),
        BackupJob('daily', timedelta(days=1), 7),
        BackupJob('weekly', timedelta(weeks=1), 4),
        BackupJob('monthly', timedelta(weeks=4), 2)
    ]

    def __init__(self, minecraft, source, dest):
        self.minecraft = minecraft
        self.source = source
        self.dest = dest

        self._pool = gevent.pool.Pool()
        self._in_backup = False

    @property
    def is_idle(self):
        return not self._in_backup

    def get_backup_name(self, job, dt=None):
        if dt is None:
            dt = datetime.now()

        return 'backup-{}-{}'.format(job.name, dt.strftime(self.FORMAT))

    def start(self):
        self._pool.spawn(self.run)

    def run(self):
        self._in_backup = True
        files = os.path.join(self.dest, 'backup-*-*.tar.xz')

        backups = defaultdict(list)
        for backup in sorted(glob.glob(files)):
            name = os.path.split(backup)[1]
            _, type, date, _ = name.split('-')
            date = datetime.strptime(date, self.FORMAT)
            backups[type].append(date)

        for job in self.BACKUPS:
            past = backups.get(job.name, [])
            self.create_backup_if_required(job, past)

        self._in_backup = False
        g = gevent.spawn_later(3600, self.run)
        self._pool.add(g)

    def create_backup_if_required(self, job, past):
        now = datetime.now()
        # past has to be sorted
        last = past[-1] if past else ZERO_TIME

        if now - last > job.delta:
            # we make a new backup, add it to the past list
            past.append(self.create_backup(job))
            # only a maximum number of backups allowed, remove
            # too old backups
            self.remove_old_backups(job, last)

    def create_backup(self, job):
        last = os.path.join(self.dest, 'last')
        gevent.subprocess.call(['rsync', '-a', '--del', self.source, last])

        now = datetime.now()
        path = os.path.join(
            self.dest, '{}.tar'.format(self.get_backup_name(job, now))
        )
        p1 = subprocess.Popen(['nice', '-n', '19', 'tar', 'cf', path, last])
        p1.communicate()
        p2 = subprocess.Popen(['nice', '-n', '19', 'xz', '-e9', path])
        p2.communicate()

        return now

    def remove_old_backups(self, job, past):
        to_delete = past[:len(past)-job.num]

        for dt in past:
            name = '{}.tar.xz'.format(self.get_backup_name(job, dt))
            path = os.path.join(self.dest, name)

            os.remove(path)


