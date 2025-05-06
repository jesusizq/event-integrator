import enum


class SellModeEnum(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"

    @classmethod
    def from_string(cls, value: str):
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"'{value}' is not a valid SellModeEnum member")
