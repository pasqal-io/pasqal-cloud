from enum import Enum
from typing import List


class StrEnum(str, Enum):
    def __str__(self) -> str:
        """Used when dumping enum fields in a schema."""
        ret: str = self.value
        return ret

    @classmethod
    def list(cls) -> List[str]:
        return list(map(lambda c: c.value, cls))  # type: ignore
