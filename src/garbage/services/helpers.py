from garbage.services.Decorators import first_empty_element


@first_empty_element
def prepare_selector_from_api_response(data):
    return [x.to_selector() for x in data]