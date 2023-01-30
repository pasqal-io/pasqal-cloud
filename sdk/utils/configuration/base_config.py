from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Optional


class InvalidConfiguration(Exception):
    pass


INVALID_KEY_ERROR_MSG = "Invalid key {} in Configuration.extra_config. Attempted to override a default field."


@dataclass
class BaseConfig:

    extra_config: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        self._validate()
        return self._unnest_extra_config(asdict(self))

    @classmethod
    def from_dict(cls, conf: dict[str, Any]) :
        base_conf = {}
        for field in fields(cls):
            if field.name != "extra_config" and field.name in conf:
                base_conf[field.name] = conf.pop(field.name)

        # ensure that no extra config is passed as None
        if not conf:
            conf = None  # type: ignore
        return cls(**base_conf, extra_config=conf)

    @staticmethod
    def _unnest_extra_config(conf_dict: dict[str, Any]) -> dict[str, Any]:
        res = {k: v for (k, v) in conf_dict.items() if not k == "extra_config"}
        if conf_dict.get("extra_config", None):
            res.update(conf_dict["extra_config"])
        return res

    def _validate(self) -> None:
        if self.extra_config:
            for k in self.extra_config.keys():
                if k in self.__dataclass_fields__.keys():
                    raise InvalidConfiguration(INVALID_KEY_ERROR_MSG.format(k))