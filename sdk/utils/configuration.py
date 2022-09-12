from dataclasses import dataclass, asdict


@dataclass
class Configuration():
    dt: float = 0.1
    precision: str = 'normal'

    def to_dict(self):
        return asdict(self)