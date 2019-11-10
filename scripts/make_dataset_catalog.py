#!/usr/bin/env python3
import sys
from argparse import ArgumentParser
from typing import List

from shinra import util
from shinra.dataset import catalog


def main(args: List[str]) -> None:
    parser = ArgumentParser()
    parser.add_argument('--dataset_dir',
                        type=str,
                        required=True,
                        help='Path to the dataset directory.')
    parser.add_argument('--output_dir',
                        type=str,
                        required=True,
                        help='Path to the output catalog directory.')
    flags = parser.parse_args(args)
    util.confirm(
        f'Making dataset catalogs in "{flags.output_dir}".\nContinue?')
    catalog.make_dataset_catalogs(flags.dataset_dir, flags.output_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
