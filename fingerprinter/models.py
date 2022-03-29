from typing import Dict, List

from pydantic import BaseModel, Field


class FingerprintTarget(BaseModel):
    depends_on: List[str] = Field(default_factory=lambda: [], alias='depends-on')

    # All directory paths are recursive.
    # Every element is a glob
    include_paths: List[str] = Field(default_factory=lambda: [], alias='include-paths')


class FingerprintConfig(BaseModel):
    ignore_paths: List[str] = Field(default_factory=lambda: ['__pycache__'], alias='ignore-paths')
    targets: Dict[str, FingerprintTarget]
