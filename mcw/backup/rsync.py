from mcw.backup import Backup
from datetime import datetime

import gevent.subprocess
import gevent


class RsyncBackup(Backup):
    def create_backup(self, name, path):
        now = datetime.now()
        name = '{}.tar'.format(self.get_backup_name(name, now))

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
            stdout=gevent.subprocess.PIPE, cwd=path
        )
        p1.communicate()
        p2 = gevent.subprocess.Popen(
            ['nice', '-n', '19', 'xz', '-e9', name],
            stdout=gevent.subprocess.PIPE, cwd=path
        )
        self._processes.append(p2)

        return now
