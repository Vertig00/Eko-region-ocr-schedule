def first_empty_element(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        match result:
            case list():
                match result[0]:
                    case tuple():
                        return [("", None)] + result
                    case dict():
                        return [{"", None}] + result
                    case _:
                        return [None] + result

            case dict():
                return {"": None, **result}

    return wrapper