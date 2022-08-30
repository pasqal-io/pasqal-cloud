from enum import Enum


class StrEnum(str, Enum):
    def __str__(self):
        """Used when dumping enum fields in a schema."""
        return self.value

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))
