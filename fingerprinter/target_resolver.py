import json
import logging
from typing import Any, Dict, List, Optional

from fingerprinter import BuildConfig, Fingerprinter
from fingerprinter.build_arg_resolver import BuildArgResolver
from fingerprinter.command_builder import DockerCommandBuilder
from fingerprinter.models import TargetOutput


class TargetResolver:
    def __init__(self, config: BuildConfig, cli_build_args: Optional[Dict[str, Any]] = None):
        self.config = config
        self.fingerprinter = Fingerprinter(self.config)
        self.cli_build_args = cli_build_args
        self.build_arg_resolver = BuildArgResolver(self.config, cli_build_args)

    @property
    def build_targets(self) -> List[str]:
        return self.resolve_layer_build_order(self.config)

    @staticmethod
    def resolve_layer_build_order(config: BuildConfig) -> List[str]:
        unordered_targets = list(config.targets.keys())
        ordered_targets = []
        _alarm_remaining_targets = None
        while len(ordered_targets) != len(unordered_targets):
            remaining_targets = set(unordered_targets).difference(set(ordered_targets))
            if _alarm_remaining_targets and _alarm_remaining_targets == len(remaining_targets):
                logging.warning(
                    f'Could not add the following targets to the build; config is invalid: {remaining_targets}.'
                )
                return ordered_targets

            _alarm_remaining_targets = len(remaining_targets)
            for t in remaining_targets:
                target = config.targets[t]
                dependencies_added = all(
                    d in ordered_targets for d in target.depends_on
                )
                if dependencies_added:
                    ordered_targets.append(t)
        # Strip out the targets that are configured not to build
        # by only including those with `build_target =~ True`
        return list(
            filter(lambda t: config.targets[t].build_target, ordered_targets)
        )

    def resolve(self, target: str, salt: str = "") -> TargetOutput:
        target_config = self.config.targets[target]

        if self.cli_build_args:
            salt += json.dumps(self.cli_build_args)

        result = TargetOutput(
            name=target,
            fingerprint=self.fingerprinter.get_fingerprint(target, salt),
        )

        if target_config.build_target:
            build_args = target_config.docker.build_args
            build_args.extend(
                self.config.docker.build_args
            )
            build_args = self.build_arg_resolver.resolve_build_args(
                result, target_config.docker.build_args
            )
            command_builder = DockerCommandBuilder(self.config)

            if not target_config.docker.target:
                target_config.docker.target = target
            result.docker_target = target_config.docker.target

            if not target_config.docker.dockerfile:
                target_config.docker.dockerfile = self.config.docker.dockerfile
            result.dockerfile = target_config.docker.dockerfile

            result.docker_command = command_builder.build_docker_command(result, build_args)

        return result
