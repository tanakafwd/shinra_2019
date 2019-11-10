#!/usr/bin/env python3
import sys
from argparse import ArgumentParser
from typing import List

from shinra import util
from shinra.dataset import arrangement


def main(args: List[str]) -> None:
    parser = ArgumentParser()
    parser.add_argument('--dataset_dir',
                        type=str,
                        required=True,
                        help='Path to the dataset directory.')
    flags = parser.parse_args(args)
    util.confirm(f'Arranging dataset in "{flags.dataset_dir}".\nContinue?')
    arrangement.arrange_dataset(flags.dataset_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
