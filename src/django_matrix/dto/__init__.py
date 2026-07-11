from dataclasses import asdict, dataclass


@dataclass
class DTO:
    def asdict(self) -> dict:
        return asdict(self)
