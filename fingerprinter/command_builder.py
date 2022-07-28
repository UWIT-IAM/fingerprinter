from typing import Any, Dict

from fingerprinter import BuildConfig
from fingerprinter.models import TargetOutput


class DockerCommandBuilder:
    """Builds a docker command from a configured target."""
    def __init__(self, config: BuildConfig):
        self.config = config

    def build_docker_command(
            self,
            target: TargetOutput,
            build_args: Dict[str, Any],
    ):
        target_config = self.config.targets[target.name]
        global_config = self.config.docker
        docker_config = target_config.docker
        if not target_config.build_target:
            return None

        # e.g., ghcr.io/uwit-iam/my-app.development-server
        image_name = f'{global_config.repository}/{global_config.app_name}.{docker_config.target}'
        tag = target.fingerprint
        image_tag = f'{image_name}:{tag}'
        target.docker_tag = image_tag
        docker_build_args = ""
        for name, val in build_args.items():
            docker_build_args += f"--build-arg {name}={val} "
        cmd = (
            f'docker build -f {target.dockerfile} '
            f'--target {target.name} '
            f'{docker_build_args}'
            f'-t {image_tag} {global_config.context}'
        )
        return cmd
