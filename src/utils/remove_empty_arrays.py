def remove_empty_arrays(obj):
    if isinstance(obj, dict):
        return {k: remove_empty_arrays(v) for k, v in obj.items() if not (isinstance(v, list) and len(v) == 0)}
    elif isinstance(obj, list):
        if len(obj) == 0:
            return None
        return [remove_empty_arrays(item) for item in obj if remove_empty_arrays(item) is not None]
    return obj