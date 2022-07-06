import argparse
import logging
import yaml

from . import Fingerprinter
from .models import FingerprintConfig


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "Given a target and an input yaml, returns the target's SHA-256 hash.\n"
        "--config-file and --target are always required.\n"
    )
    parser.add_argument('--config-file', '-f', required=True,
                        help='The config file you want to use to generate fingerprints.')
    parser.add_argument('--target', '-t', required=True,
                        help='The target from the config file whose fingerprint you want to get')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                        help='Set log level to INFO')
    parser.add_argument('--debug', '-g', action='store_true', default=False,
                        help='Set log level to DEBUG')
    parser.add_argument('--salt', action='store', default='',
                        help='Use this to help differentiate one build from another based on dynamic context. Any value is accepted.')
    return parser


def load_yaml(filename: str) -> FingerprintConfig:
    with open(filename) as f:
        return FingerprintConfig.parse_obj(yaml.load(f, Loader=yaml.SafeLoader))


def main():
    args = get_parser().parse_args()
    config = load_yaml(args.config_file)
    log_level = logging.WARNING

    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level)
    logging.debug("Starting in DEBUG mode")

    fp = Fingerprinter(config)
    print(fp.get_fingerprint(args.target, args.salt))


if __name__ == "__main__":
    main()
