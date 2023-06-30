import functools

def list_to_dict(data):
    output = dict()
    for i in data:
        output[i['id']] = i
    return output

def isnull_to_none(value):
    return None if value == 'null' else value

def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))

def get_request_param(request, param, default_val=None):
    val = request.query_params.get(param)
    if val in (None, 'None', 'null', 'undefined'):
        return default_val
    return val
