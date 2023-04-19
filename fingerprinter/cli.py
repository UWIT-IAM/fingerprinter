import argparse
import logging
import os.path
import textwrap

import yaml

from fingerprinter.target_resolver import TargetResolver
from .models import BuildConfig


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""
        This tool can be used to build deterministic fingerprints, that
        are smartly flagged for updates based on configuration you provide.
        For full documentation, please refer to the README at
            https://github.com/uwit-iam/fingerprinter/tree/main/README.md


        Behavior is mainly controlled by the output type (-o/--output):

        js/json        REQUIRES: -t/--target
                                 -c/--config (if not default)
                       OUTPUTS: the json build configuration for the target
                       This is the default output type

        pjs/pretty-json
                       Same as js/json, but the output is easier to read

        build-script   OUTPUTS: The absolute path to the 'build-fp-targets.sh' script.

        build-targets  REQUIRES: -c/c--config (if not default)
                       OUTPUTS: An acceptable order in which to build all configured targets

        """),
        usage="fingerprinter [-o <OUTPUT_TYPE>] [-f <CONFIGURATION_FILE] [-t TARGET] [OPTIONS]",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('--config-file', '-f', default='fingerprints.yaml',
                        help='The config file you want to use to generate fingerprints.')
    parser.add_argument('--target', '-t', required=False, default=None,
                        help='The target from the config file whose configuration you want to get')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                        help='Set log level to INFO')
    parser.add_argument('--debug', '-g', action='store_true', default=False,
                        help='Set log level to DEBUG')
    parser.add_argument('--salt', action='store', default='',
                        help='Use this to help differentiate one build '
                             'from another based on dynamic context. Any value is accepted.')
    parser.add_argument('--output', '-o', default='json',
                        help='fingerprint/fp, build-script, build-targets, '
                             'json/js, pretty-json/pjs, query/q, release-target')
    parser.add_argument(
        '--build-arg',
        action='append',
        help="Can be provided multiple times. Any build arg provided this way will be "
             "treated as salt, but only build-args declared in the build configuration file "
             "will be passed into docker. This is to prevent awkward vulnerabilities."
    )
    return parser


def load_yaml(filename: str) -> BuildConfig:
    with open(filename) as f:
        return BuildConfig.parse_obj(yaml.load(f, Loader=yaml.SafeLoader))


here = os.path.abspath(os.path.dirname(__file__))


def main():
    args = get_parser().parse_args()

    if args.output == 'build-script':
        print(os.path.join(here, 'build.sh'))
        return

    config = load_yaml(args.config_file)

    if args.output == 'release-target':
        print(config.release_target)
        return

    log_level = logging.WARNING
    # turns '--build-arg foo=blah --build-arg blip=blorp' into
    # {"foo": "blah", "blip": "blorp"}
    build_args = args.build_arg if args.build_arg else []
    build_args = {
        k: v for k, v in [
            a.split('=') for a in build_args
        ]
    }

    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level)
    logging.debug("Starting in DEBUG mode")

    resolver = TargetResolver(config, cli_build_args=build_args)

    if args.output == 'build-targets':
        print(' '.join(resolver.build_targets))
        return

    if 'js' not in args.output:
        raise ValueError(f'{args.output} is not a valid output type.')

    indent = 2 if args.output.startswith('p') else None

    result = resolver.resolve(args.target)
    print(result.json(by_alias=True, indent=indent))


if __name__ == "__main__":
    main()
