import os
from typing import Any, Dict, List

from fingerprinter import BuildConfig
from fingerprinter.models import BuildArgConfig, TargetOutput


class BuildArgResolver:
    def __init__(self, config: BuildConfig, cli_args: Dict[str, Any]):
        self.config = config
        self.cli_args = cli_args

    @staticmethod
    def get_value_from_env(arg: str):
        return os.environ.get(arg)

    def get_value_from_cli(self, arg: str):
        return self.cli_args.get(arg)

    def get_value_from_target(self, target: str, field: str):
        from fingerprinter.target_resolver import TargetResolver
        resolver = TargetResolver(self.config, self.cli_args)
        value = getattr(resolver.resolve(target), field, None)
        return value

    def resolve_build_args(self, target_output: TargetOutput, target_build_args: List[BuildArgConfig]) -> Dict[str,
                                                                                                              Any]:
        result = {}
        for arg in target_build_args:
            name = arg.arg
            value = None
            for source in arg.sources:
                if value:
                    break
                if source == 'env':
                    value = self.get_value_from_env(name)
                elif source == 'cli':
                    value = self.get_value_from_cli(name)
                elif source.startswith('target'):
                    _,  t_name, t_field = source.split(':')
                    if t_name == target_output.name:
                        value = getattr(target_output, t_field)
                    else:
                        value = self.get_value_from_target(t_name, t_field)

            if not value:
                raise ValueError(
                    f'Expected to find a value for build arg {name} '
                    f'in any source from {arg.sources}, but no value was provided.'
                )
            result[arg.arg] = value
        return result
