#!/usr/bin/env python3
import csv
import os
import re
from argparse import ArgumentParser
from collections import namedtuple
from multiprocessing import Pool
from typing import Any, Dict, Generator, List, Tuple

from bs4 import BeautifulSoup
from tqdm import tqdm

from shinra import dataset, util
from shinra.logger import get_logger

_LOG = get_logger()

_AnnotationInfo = namedtuple(
    '_AnnotationInfo', ('num_annotations', 'attribute_counts'))


def _get_annotation_info(annotation_file_path: str) \
        -> Tuple[Tuple[str, ...], Dict[int, _AnnotationInfo]]:
    lines_by_page_id = dataset.read_annotation_lines_by_page_id(
        annotation_file_path)
    attributes = tuple(sorted(frozenset(
        str(dataset.parse_annotation_line(line)['attribute'])
        for lines in lines_by_page_id.values()
        for line in lines)))
    attribute_to_index = {attribute: i for (
        i, attribute) in enumerate(attributes)}
    zero_attribute_counts = [0 for unused in range(len(attributes))]
    annotation_info_by_page_id: Dict[int, _AnnotationInfo] = {}
    for (page_id, lines) in lines_by_page_id.items():
        num_annotations = len(lines)
        attribute_counts = zero_attribute_counts[:]
        for line in lines:
            attribute = dataset.parse_annotation_line(line)['attribute']
            attribute_counts[attribute_to_index[attribute]] += 1
        annotation_info_by_page_id[page_id] = _AnnotationInfo(
            num_annotations=num_annotations,
            attribute_counts=tuple(attribute_counts))
    return (attributes, annotation_info_by_page_id)


_RE_CLEAN_TITLE = re.compile(r'\s*-\s+Wikipedia Dump.*$')


def _clean_title(title: str) -> str:
    return _RE_CLEAN_TITLE.sub('', title)


def _get_html_info(html_file_path: str) -> Tuple[str, int]:
    with open(html_file_path, 'r') as fin:
        soup = BeautifulSoup(fin, 'lxml')  # Or 'html5lib'
        title = _clean_title(soup.title.string)
        infobox_count = len(soup.find_all(class_='infobox'))
        return (title, infobox_count)


_FileInfoTaskArgs = namedtuple('_FileInfoTaskArgs', (
    'page_id', 'html_file_path', 'text_file_path'))
_FileInfoTaskResult = namedtuple('_FileInfoTaskResult', (
    'page_id', 'title', 'html_file_size', 'text_file_size', 'infobox_count'))


def _file_info_task(args: _FileInfoTaskArgs) -> _FileInfoTaskResult:
    (title, infobox_count) = _get_html_info(args.html_file_path)
    return _FileInfoTaskResult(
        page_id=args.page_id,
        title=title,
        html_file_size=os.path.getsize(args.html_file_path),
        text_file_size=os.path.getsize(args.text_file_path),
        infobox_count=infobox_count)


def _add_values(base: List[int], sub: Tuple[int]) -> None:
    for i in range(len(base)):
        base[i] += sub[i]


def _transpose(matrix: List[Tuple[Any, ...]]) \
        -> Generator[Tuple[Any, ...], None, None]:
    max_column_size = max(len(row) for row in matrix)
    for i in range(max_column_size):
        yield tuple(row[i] if i < len(row) else None
                    for row in matrix)


def make_category_dataset_catalogs(
        dataset_dir: str, output_catalog_dir: str, category: str) \
        -> Tuple[Tuple[Any, ...], Tuple[Any, ...]]:
    answer_annotation_file_path = os.path.join(
        dataset.make_annotation_dir_path(dataset_dir), f'{category}_dist.json')
    (attributes, annotation_info_by_page_id) = _get_annotation_info(
        answer_annotation_file_path)
    html_dir_path = dataset.make_html_dir_path(dataset_dir, category)
    text_dir_path = dataset.make_text_dir_path(dataset_dir, category)
    file_info_task_args_list = []
    for file_name in os.listdir(html_dir_path):
        assert file_name.endswith('.html')
        page_id = dataset.get_page_id_from_file_path(file_name)
        file_info_task_args_list.append(_FileInfoTaskArgs(
            page_id=page_id,
            html_file_path=os.path.join(html_dir_path, f'{page_id}.html'),
            text_file_path=os.path.join(text_dir_path, f'{page_id}.txt')))
    with Pool() as pool:
        file_info_by_page_id = {
            result.page_id: result
            for result in tqdm(pool.imap_unordered(_file_info_task,
                                                   file_info_task_args_list,
                                                   chunksize=100),
                               total=len(file_info_task_args_list))}
    catalog_file_path = os.path.join(
        output_catalog_dir, f'{category}_catalog.csv')
    with open(catalog_file_path, 'w') as fout:
        writer = csv.writer(fout, lineterminator='\n')
        writer.writerow(('page_id', 'title', 'html_file_size', 'text_file_size',
                         'infobox_count', 'num_annotations', *attributes))
        empty_annotation_info = _AnnotationInfo(
            num_annotations=None,
            attribute_counts=tuple(None for unused in range(len(attributes))))
        num_pages = 0
        total_html_file_size = 0
        total_text_file_size = 0
        total_infobox_count = 0
        num_pages_with_annotation = 0
        num_pages_with_infobox = 0
        total_num_annotations = 0
        attribute_counts = list(0 for unused in range(len(attributes)))
        for page_id in sorted(file_info_by_page_id.keys()):
            file_info = file_info_by_page_id[page_id]
            annotation_info = annotation_info_by_page_id.get(
                page_id, empty_annotation_info)
            writer.writerow((page_id,
                             file_info.title,
                             file_info.html_file_size,
                             file_info.text_file_size,
                             file_info.infobox_count,
                             annotation_info.num_annotations,
                             *annotation_info.attribute_counts))
            num_pages += 1
            total_html_file_size += file_info.html_file_size
            total_text_file_size += file_info.text_file_size
            total_infobox_count += file_info.infobox_count
            if annotation_info.num_annotations is not None:
                num_pages_with_annotation += 1
                total_num_annotations += annotation_info.num_annotations
                _add_values(attribute_counts, annotation_info.attribute_counts)
            if file_info.infobox_count > 0:
                num_pages_with_infobox += 1
    return (('category',
             'num_pages',
             'total_html_file_size',
             'total_text_file_size',
             'total_infobox_count',
             'num_pages_with_annotation',
             'num_pages_with_infobox',
             'num_attribute_types',
             'total_num_annotations',
             *attributes),
            (category,
             num_pages,
             total_html_file_size,
             total_text_file_size,
             total_infobox_count,
             num_pages_with_annotation,
             num_pages_with_infobox,
             len(attributes),
             total_num_annotations,
             *attribute_counts))


def make_dataset_catalogs(dataset_dir: str, output_catalog_dir: str) -> None:
    summary_rows: List[Tuple[Any, ...]] = []
    util.makedirs(output_catalog_dir)
    for category in tqdm(sorted(dataset.ALL_CATEGORIES),
                         total=len(dataset.ALL_CATEGORIES)):
        summary_rows.extend(make_category_dataset_catalogs(
            dataset_dir, output_catalog_dir, category))
    catalog_summary_file_path = os.path.join(
        output_catalog_dir, 'summary_catalog.csv')
    with open(catalog_summary_file_path, 'w') as fout:
        writer = csv.writer(fout)
        for row in _transpose(summary_rows):
            writer.writerow(row)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('--dataset_dir',
                        type=str,
                        required=True,
                        help='Path to the dataset directory.')
    parser.add_argument('--output_catalog_dir',
                        type=str,
                        required=True,
                        help='Path to the output catalog directory.')
    (flags, unparsed) = parser.parse_known_args()
    util.confirm(
        f'Making dataset catalogs in "{flags.output_catalog_dir}".\nContinue?')
    make_dataset_catalogs(flags.dataset_dir, flags.output_catalog_dir)


if __name__ == '__main__':
    main()
