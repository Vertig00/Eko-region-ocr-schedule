def first_empty_element(func):
    def wrapper(*args, **kwargs):
        return [("", None)] + func(*args, **kwargs)
    return wrapper