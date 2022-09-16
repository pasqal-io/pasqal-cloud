import dataclasses
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
        return Configuration._flatten_dict(asdict(self))

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
    def _flatten_dict(
        conf_dict: Optional[Union[Dict[str, Any], str]], prefix: str = ""
    ) -> Dict:
        """flattens dictionaries, except the extra_config field.
        Excludes None values
        """
        if not conf_dict:
            return {}
        if prefix == "extra_config":
            #  In extra_config don't flatten the further dicts.
            return {k: v for (k, v) in conf_dict.items()}
        return (
            {  # flatten if (nested) dictionary
                kk: vv
                for (k, v) in conf_dict.items()
                for (kk, vv) in Configuration._flatten_dict(v, k).items()
            }
            if isinstance(conf_dict, dict)
            else {prefix: conf_dict}
        )
