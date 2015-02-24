from mcw.backup import Backup, on_backup_started, on_backup_stopped
from datetime import datetime
import os.path

import gevent.subprocess
import gevent


class RsyncBackup(Backup):
    EXTENSION = 'tar.xz'

    def create_backup(self, type, label=None):
        now = datetime.now()
        name = '{}.tar'.format(self.get_backup_name(type, now))
        final_name = '{}.xz'.format(name)

        on_backup_started.send(self, type=type, name=final_name, label=label)

        self.minecraft._write('save-all\nsave-off\n')
        # todo wait for server message instead of this sleep
        gevent.sleep(5)
        gevent.subprocess.call([
            'rsync', '-a', '--del', '{}/'.format(self.source), self._last]
        )
        self.minecraft._write('save-on\nsave-all\n')

        parent = self._last
        folder = self.world
        if not self.worldonly:
            parent = self.path
            folder = 'server'

        p1 = gevent.subprocess.Popen(
            ['nice', '-n', '19', 'tar',
             'cf', name, '-C', parent, folder, '--force-local'],
            stdout=gevent.subprocess.PIPE, cwd=self.path
        )
        p1.communicate()
        p2 = gevent.subprocess.Popen(
            ['nice', '-n', '19', 'xz', '-e9', name],
            stdout=gevent.subprocess.PIPE, cwd=self.path
        )
        self._processes.append(p2)

        if label is not None:
            self.metadata[final_name] = label

        def stopped_event():
            p2.wait()
            on_backup_stopped.send(
                self, type=type, name=final_name, label=label, date=now,
                size=os.path.getsize(os.path.join(self.path, final_name))
            )

        self._pool.spawn(stopped_event)

        return (now, name)
