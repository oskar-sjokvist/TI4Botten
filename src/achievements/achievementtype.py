from dataclasses import dataclass

from typing import Optional

@dataclass
class Achieved:
    """Marker for an achieved achievement."""
@dataclass
class Unlocked:
    """Marker for an already unlocked achievement."""

@dataclass
class Locked:
    current: Optional[int]
    target: Optional[int]


AchievementType = Achieved|Unlocked|Locked|str