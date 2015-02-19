from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import os.path
import glob
import os

import gevent.subprocess
import gevent.pool
import gevent


BackupJob = namedtuple('BackupJob', ['name', 'delta', 'num'])


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
        self._processes = list()

    @property
    def is_idle(self):
        # all unfinished processes
        self._processes = [p for p in self._processes if p.poll() is None]
        # not _in_backup and no process running
        return not self._in_backup and len(self._processes) == 0

    def get_backup_name(self, job, dt=None):
        if dt is None:
            dt = datetime.now()

        return 'backup-{}-{}'.format(job.name, dt.strftime(self.FORMAT))

    def start(self, delay=600):
        last = os.path.join(self.dest, 'server')
        if not os.path.exists(last):
            os.makedirs(last)

        def exc(gr):
            self._in_backup = False

        g = gevent.spawn_later(delay, self.run)
        g.link_exception(exc)
        self._pool.add(g)

    def run(self):
        self._in_backup = True
        files = os.path.join(self.dest, 'backup-*-*.tar.xz')

        backups = defaultdict(list)
        for backup in sorted(glob.glob(files)):
            name = os.path.split(backup)[1]
            try:
                _, type, date = name.split('-', 2)
                date = date.split('.', 1)[0]
                date = datetime.strptime(date, self.FORMAT)
            except (ValueError, IndexError):
                continue
            backups[type].append(date)

        for job in self.BACKUPS:
            past = backups.get(job.name, [])
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
            past.append(self.create_backup(job))
            # only a maximum number of backups allowed, remove
            # too old backups
            self.remove_old_backups(job, past)

    def create_backup(self, job):
        last = os.path.join(self.dest, 'server')
        self.minecraft._write('save-all\nsave-off\n')
        # todo wait for server message instead of this sleep
        gevent.sleep(5)
        gevent.subprocess.call([
            'rsync', '-a', '--del', '{}/'.format(self.source), last]
        )
        self.minecraft._write('save-on\nsave-all\n')

        now = datetime.now()
        name = '{}.tar'.format(self.get_backup_name(job, now))
        p1 = gevent.subprocess.Popen(
            ['nice', '-n', '19', 'tar',
             'cf', name, '-C', last, 'world', '--force-local'],
            stdout=gevent.subprocess.PIPE, cwd=self.dest
        )
        p1.communicate()
        p2 = gevent.subprocess.Popen(
            ['nice', '-n', '19', 'xz', '-e9', name],
            stdout=gevent.subprocess.PIPE, cwd=self.dest
        )
        self._processes.append(p2)

        return now

    def remove_old_backups(self, job, past):
        to_delete = past[:max(0, len(past)-job.num)]

        for dt in to_delete:
            name = '{}.tar.xz'.format(self.get_backup_name(job, dt))
            path = os.path.join(self.dest, name)

            os.remove(path)


