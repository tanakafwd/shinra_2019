#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from multiprocessing import Pool
from tempfile import TemporaryDirectory
from typing import List, NamedTuple, Set

from tqdm import tqdm

from shinra import dataset, util
from shinra.logger import get_logger

_LOG = get_logger()


class DatasetArrangerException(Exception):
    pass


def _unzip(zip_file_path: str, output_dir: str) -> None:
    # Call `tar` or `unzip` because zipfile.ZipFile does not work for the SHINRA
    # 2019 dataset.
    util.makedirs(output_dir)
    system = platform.system()
    if system == 'Darwin':  # Mac
        command = ' '.join(('tar', 'xf', zip_file_path, '-C', output_dir))
    elif system == 'Linux':
        command = ' '.join(('unzip', zip_file_path, '-d', output_dir))
    else:
        raise DatasetArrangerException(f'Unsupported system: {system}')
    proc = subprocess.Popen(command,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    proc.communicate()
    if proc.returncode != 0:
        _LOG.warning(f'Non-zero code returned: {proc.returncode}')


class _UnzipTaskArgs(NamedTuple):
    zip_file_path: str
    expected_md5_digest: str
    output_dir: str


def _unzip_task(args: _UnzipTaskArgs) -> None:
    md5_digest = util.md5(args.zip_file_path)
    if md5_digest != args.expected_md5_digest:
        raise DatasetArrangerException(
            'MD5 digest mismatch: '
            f'actual:{md5_digest} expected:{args.expected_md5_digest}'
        )
    return _unzip(args.zip_file_path, args.output_dir)


class _UnzipInsideTaskArgs(NamedTuple):
    zip_file_path: str
    output_dir: str


def _unzip_inside_task(args: _UnzipInsideTaskArgs) -> None:
    return _unzip(args.zip_file_path, args.output_dir)


class _MoveTaskArgs(NamedTuple):
    src_file_path: str
    dst_file_path: str


def _move_task(args: _MoveTaskArgs) -> None:
    if os.path.getsize(args.src_file_path) == 0:
        _LOG.warning(f'Skip empty file: {args.src_file_path}')
        return
    shutil.move(args.src_file_path, args.dst_file_path)
    # TODO: Compress the file by gzip if needed.
    os.chmod(args.dst_file_path, 0o444)


def arrange_dataset(dataset_dir: str) -> None:
    with TemporaryDirectory(dir=dataset_dir) as tmp_dir:
        _LOG.info('Unzipping the dataset zip files.')
        unzip_task_args_list = tuple(
            _UnzipTaskArgs(
                zip_file_path=os.path.join(dataset_dir, dataset_file_name),
                expected_md5_digest=md5_digest,
                output_dir=os.path.join(tmp_dir, dataset_file_name))
            for (dataset_file_name,
                 md5_digest) in dataset.DATASET_FILE_NAMES.items())
        with Pool() as pool:
            for unused in tqdm(pool.imap(_unzip_task,
                                         unzip_task_args_list,
                                         chunksize=1),
                               total=len(unzip_task_args_list)):
                pass
        _LOG.info('Unzipping zip files inside the dataset zip files.')
        unzip_inside_task_args_list = []
        for dataset_file_name in dataset.DATASET_FILE_NAMES.keys():
            for (root, unused,
                 files) in os.walk(os.path.join(tmp_dir, dataset_file_name)):
                for file_name in files:
                    if not file_name.endswith('.zip'):
                        continue
                    zip_file_path = os.path.join(root, file_name)
                    if os.path.getsize(zip_file_path) == 0:
                        _LOG.warning(f'Skip empty zip file: {zip_file_path}')
                        continue
                    unzip_inside_task_args_list.append(
                        _UnzipInsideTaskArgs(
                            zip_file_path=zip_file_path,
                            output_dir=os.path.splitext(zip_file_path)[0]))
        with Pool() as pool:
            for unused in tqdm(pool.imap(_unzip_inside_task,
                                         unzip_inside_task_args_list,
                                         chunksize=1),
                               total=len(unzip_inside_task_args_list)):
                pass
        _LOG.info('Moving files.')
        move_task_args_list = []
        for dataset_file_name in dataset.DATASET_FILE_NAMES.keys():
            for (root, unused,
                 files) in os.walk(os.path.join(tmp_dir, dataset_file_name)):
                category = dataset.get_category_from_dir_path(root)
                for file_name in files:
                    dst_file_path = None
                    if file_name.endswith('.json'):
                        dst_file_path = os.path.join(
                            dataset.make_annotation_dir_path(dataset_dir),
                            file_name)
                    elif category is not None:
                        if file_name.endswith('.html'):
                            dst_file_path = os.path.join(
                                dataset.make_html_dir_path(
                                    dataset_dir, category),
                                file_name)
                        elif file_name.endswith('.txt'):
                            dst_file_path = os.path.join(
                                dataset.make_text_dir_path(
                                    dataset_dir, category),
                                file_name)
                    if dst_file_path is None:
                        continue
                    move_task_args_list.append(
                        _MoveTaskArgs(
                            src_file_path=os.path.join(root, file_name),
                            dst_file_path=dst_file_path))
        for dst_dir in frozenset(
                os.path.dirname(move_task_args.dst_file_path)
                for move_task_args in move_task_args_list):
            util.makedirs(dst_dir)
        with Pool() as pool:
            for unused in tqdm(pool.imap(_move_task,
                                         move_task_args_list,
                                         chunksize=500),
                               total=len(move_task_args_list)):
                pass
    _LOG.info('Validating the arranged data.')
    for category in dataset.ALL_CATEGORIES:
        assert os.path.exists(
            os.path.join(dataset.make_annotation_dir_path(dataset_dir),
                         f'{category}_dist.json'))
        assert os.path.exists(
            os.path.join(dataset.make_annotation_dir_path(dataset_dir),
                         f'{category}_dist_for_view.json'))
        html_page_ids: Set[int] = set()
        for file_name in os.listdir(dataset.make_html_dir_path(dataset_dir,
                                                               category)):
            page_id = dataset.get_page_id_from_file_path(file_name)
            assert page_id not in html_page_ids
            html_page_ids.add(page_id)
        text_page_ids: Set[int] = set()
        for file_name in os.listdir(dataset.make_text_dir_path(dataset_dir,
                                                               category)):
            page_id = dataset.get_page_id_from_file_path(file_name)
            assert page_id not in text_page_ids
            text_page_ids.add(page_id)
        assert html_page_ids
        assert text_page_ids
        assert html_page_ids == text_page_ids


def main(args: List[str]) -> None:
    parser = ArgumentParser()
    parser.add_argument('--dataset_dir',
                        type=str,
                        required=True,
                        help='Path to the dataset directory.')
    flags = parser.parse_args(args)
    util.confirm(f'Arranging dataset in "{flags.dataset_dir}".\nContinue?')
    arrange_dataset(flags.dataset_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
