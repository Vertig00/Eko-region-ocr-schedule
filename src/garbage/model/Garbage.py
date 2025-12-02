
class GarbageRegistry:
    registry = []

    @classmethod
    def register(cls, garbage_cls):
        cls.registry.append(garbage_cls)
        return garbage_cls

class Garbage:

    name = "generic"
    hash_id = "#generic"
    color = "#ff5a00"
    match_patterns = []

@GarbageRegistry.register
class Bio(Garbage):
    name = "Bio"
    hash_id = "#bio"
    color = "#814734"
    match_patterns = ["Bio"]

@GarbageRegistry.register
class Plastic(Garbage):
    name = "Metale i tworzywa sztuczne"
    hash_id = "#plastik"
    color = "#ffcd01"
    match_patterns = ["Metale tworzywa sztuczne", "Metale i tworzywa sztuczne", "Metale", "Plastik"]

@GarbageRegistry.register
class Mixed(Garbage):
    name = "Zmieszane odpady komunalne"
    hash_id = "#zmieszane"
    color = "#323232"
    match_patterns = ["Zmieszane odpady komunalne", "Zmieszane"]

@GarbageRegistry.register
class Paper(Garbage):
    name = "Papier"
    hash_id = "#papier"
    color = "#1f7dcb"
    match_patterns = ["papier"]

@GarbageRegistry.register
class Glass(Garbage):
    name = "Szkło"
    hash_id = "#szkło"
    color = "#20962a"
    match_patterns = ["Szkło"]
