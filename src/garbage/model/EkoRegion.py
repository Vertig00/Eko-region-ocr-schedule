from dataclasses import dataclass
from typing import Optional

@dataclass
class ResponseData:
    name: str
    inhabited: Optional[str]
    uninhabited: Optional[str]
    has_street: bool = False
    streets_link: Optional[str] = None

    def __post_init__(self):
        if self.uninhabited and self.uninhabited == "#":
            self.uninhabited = None

        if self.inhabited and self.inhabited == "#":
            self.inhabited = None
