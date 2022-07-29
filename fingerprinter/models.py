from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class BuildArgConfig(BaseModel):
    class Config:
        allow_population_by_field_name = True

    arg: str
    sources: List[str] = ['cli', 'env']


class DockerConfig(BaseModel):
    class Config:
        allow_population_by_field_name = True

    repository: Optional[str]
    context: str = '.'
    dockerfile: str = 'Dockerfile'
    build_args: List[BuildArgConfig] = Field(default_factory=list, alias='build-args')
    app_name: Optional[str] = Field(None, alias='app-name')


class TargetDockerConfig(BaseModel):
    class Config:
        allow_population_by_field_name = True

    dockerfile: Optional[str] = None
    target: Optional[str] = None
    build_args: List[BuildArgConfig] = Field(default_factory=list, alias='build-args')


class FingerprintTarget(BaseModel):
    class Config:
        allow_population_by_field_name = True

    depends_on: List[str] = Field(default_factory=list, alias='depends-on')

    # All directory paths are recursive. Every element is a glob
    include_paths: List[str] = Field(default_factory=list, alias='include-paths')
    docker: TargetDockerConfig = TargetDockerConfig()
    build_target: bool = Field(True, alias='build-target')


class BuildConfig(BaseModel):
    class Config:
        allow_population_by_field_name = True
    ignore_paths: List[str] = Field(default_factory=list, alias='ignore-paths')
    targets: Dict[str, FingerprintTarget]
    docker: DockerConfig = DockerConfig()
    release_target: Optional[str] = Field(None, alias='release-target')


class TargetOutput(BaseModel):
    class Config:
        allow_population_by_field_name = True
    name: str
    dockerfile: Optional[str]
    docker_target: Optional[str] = Field(None, alias='dockerTarget')
    fingerprint: str
    docker_command: Optional[str] = Field(None, alias='dockerCommand')
    docker_tag: Optional[str] = Field(None, alias='dockerTag')

    @property
    def docker_build_command(self) -> str:
        return (
            f"docker build"
        )
