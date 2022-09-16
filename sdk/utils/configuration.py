from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union

INVALID_KEY_ERROR_MSG = "Invalid key {} in Configuration.extra_config. Attempted to override a default field."
DT_VALUE_NOT_VALID = "dt must be larger than 0. Not {}."
PRECISION_NOT_VALID = "Precision {} not valid. Must be one of 'low', 'normal', 'high'"


class InvalidConfiguration(Exception):
    pass


@dataclass
class Configuration:
    dt: float = 0.1
    precision: str = "normal"
    extra_config: Optional[Dict[str, Any]] = None

    def to_dict(self):
        self._validate()
        return Configuration._unnest_extra_config(asdict(self))

    def _validate(self):
        if self.dt <= 0:
            raise InvalidConfiguration(DT_VALUE_NOT_VALID.format(self.dt))
        if self.precision not in ["low", "normal", "high"]:
            raise InvalidConfiguration(PRECISION_NOT_VALID.format(self.precision))
        if self.extra_config:
            for k in self.extra_config.keys():
                if k in self.__dataclass_fields__.keys():
                    raise InvalidConfiguration(INVALID_KEY_ERROR_MSG.format(k))
        return self

    @staticmethod
    def _unnest_extra_config(conf_dict) -> Dict:
        res = { k:v for (k,v) in conf_dict.items() if not k == "extra_config"}
        if conf_dict.get("extra_config", None):
            res.update(conf_dict["extra_config"])
        return res
