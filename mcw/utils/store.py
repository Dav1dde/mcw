#from collections.abc import MutableMapping
from collections import MutableMapping
import json
import os


class JsonStoreException(Exception):
    pass


class JsonStore(MutableMapping):
    def __init__(self, path, default=None):
        self.path = path
        self.default = default
        if self.default is None:
            self.default = dict()

        self.obj = None
        self.reload()

    def reload(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                obj = json.load(f)
                if not isinstance(obj, dict):
                    raise JsonStoreException(
                        'Invalid json store, root of '
                        'json must be an object/dictionary'
                    )
                self.obj = self.default.copy()
                self.obj.update(obj)
        else:
            self.obj = self.default.copy()

    def write(self):
        with open(self.path, 'w') as f:
            json.dump(self.obj, f)

    def __getitem__(self, key):
        return self.obj[key]

    def __setitem__(self, key, value):
        self.obj[key] = value
        self.write()

    def __delitem__(self, key):
        del self.obj[key]
        self.write()

    def __iter__(self):
        return iter(self.obj)

    def __len__(self):
        return len(self.obj)

    def __str__(self):
        return self.obj.__str__()

    def __repr__(self):
        return self.obj.__repr__()


