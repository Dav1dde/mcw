
class DummyBackup(object):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def collect_backups(cls, path):
        return dict()

    @property
    def is_idle(self):
        return True

    def get_backup_name(self, name, dt=None):
        return ''

    def start(self, delay=600):
        pass

    def run(self):
        pass

    def create_backup_if_required(self, job, past, force=False):
        pass

    def create_user_backup(self, name):
        pass

    def create_backup(self, name, path):
        pass

    def remove_old_backups(self, job, past):
        pass

