#!/usr/bin/env python3
import sys
from argparse import ArgumentParser
from typing import List

from shinra import util
from shinra.inspection import annotation


def main(args: List[str]) -> None:
    parser = ArgumentParser()
    parser.add_argument('--dataset_dir',
                        type=str,
                        required=True,
                        help='Path to the dataset directory.')
    parser.add_argument('--output_dir',
                        type=str,
                        required=True,
                        help='Path to the output directory.')
    flags = parser.parse_args(args)
    util.confirm(
        f'Inspecting annotations in "{flags.dataset_dir}".\nContinue?')
    annotation.inspect_annotations(flags.dataset_dir, flags.output_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
