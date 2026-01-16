from enum import Enum
from dataclasses import dataclass
from typing import Literal

class WinnerLabel(str, Enum):
    PLAINTIFF_WON = "plaintiff_won"
    DEFENDANT_WON = "defendant_won"
    UNCLEAR = "unclear"

@dataclass
class PredictionResult:
    prediction: WinnerLabel | None
    confidence: float
    model_version: str | None

class WinnerClassifierMode(str, Enum):
    OFF = "off"
    INFER = "infer"
    TEACH = "teach"

class WinnerBootstrapMode(str, Enum):
    OFF = "off"
    AUTO = "auto"
    FORCE = "force"
