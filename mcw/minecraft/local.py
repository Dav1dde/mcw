import os.path


def _get_type(val, *types):
    if not types:
        types = (int, float, str)
    for f in types:
        try:
            return f(val)
        except ValueError:
            pass
    return val


def _bool(val):
    return val.lower() in ('yes', 'true', '1')


def server_properties(base_path):
    path = os.path.join(base_path, 'server.properties')

    ret = dict()
    with open(path) as f:
        lines = filter(lambda a: not a.startswith('#'), (l.strip() for l in f))
        for line in lines:
            try:
                key, value = line.split('=')
            except ValueError:
                continue

            ret[key.lower()] = _get_type(value, int, float, _bool, str)

    return ret





