from typing import Dict, List

from pydantic import BaseModel, Field


class FingerprintTarget(BaseModel):
    class Config:
        allow_population_by_field_name = True

    depends_on: List[str] = Field(default_factory=lambda: [], alias='depends-on')

    # All directory paths are recursive.
    # Every element is a glob
    include_paths: List[str] = Field(default_factory=lambda: [], alias='include-paths')


class FingerprintConfig(BaseModel):
    class Config:
        allow_population_by_field_name = True
    ignore_paths: List[str] = Field(default_factory=lambda: [], alias='ignore-paths')
    targets: Dict[str, FingerprintTarget]
