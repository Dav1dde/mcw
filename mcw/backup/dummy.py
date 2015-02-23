
class DummyBackup(object):
    def __init__(self, *args, **kwargs):
        pass

    @property
    def is_idle(self):
        return True

    def get_backup_name(self, job, dt=None):
        return 'dummy'

    def start(self, delay=600):
        pass

    def run(self):
        pass

    def create_backup_if_required(self, job, past, force=False):
        pass

    def create_backup(self, job):
        pass

    def remove_old_backups(self, job, past):
        pass


