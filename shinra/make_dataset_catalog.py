#!/usr/bin/env python3
import os
import re
import sys
from argparse import ArgumentParser
from collections import defaultdict
from multiprocessing import Pool
from typing import Any, DefaultDict, Dict, Generator, List, NamedTuple, Tuple

from bs4 import BeautifulSoup
from tqdm import tqdm

from shinra import dataset, util


def _make_file_name(prefix: str) -> str:
    return f'{prefix}_catalog.csv'


class _AnnotationInfo(NamedTuple):
    num_annotations: int
    attribute_counts: DefaultDict[str, int]


def _get_annotation_info(annotation_file_path: str) \
        -> Tuple[Tuple[str, ...], Dict[int, _AnnotationInfo]]:
    annotations_by_page_id = dataset.read_annotations_by_page_id(
        annotation_file_path)
    annotation_info_by_page_id: Dict[int, _AnnotationInfo] = {}
    attributes = set()
    for (page_id, annotations) in annotations_by_page_id.items():
        num_annotations = len(annotations)
        attribute_counts: DefaultDict[str, int] = defaultdict(int)
        for annotation in annotations:
            attribute = annotation.attribute
            attribute_counts[attribute] += 1
            attributes.add(attribute)
        annotation_info_by_page_id[page_id] = _AnnotationInfo(
            num_annotations=num_annotations,
            attribute_counts=attribute_counts)
    return (tuple(sorted(attributes)), annotation_info_by_page_id)


_RE_CLEAN_TITLE = re.compile(r'\s*-\s+Wikipedia Dump.*$')


def _clean_title(title: str) -> str:
    return _RE_CLEAN_TITLE.sub('', title)


class _HtmlInfoResult(NamedTuple):
    title: str
    is_disambiguation_page: bool
    infobox_count: int


def _get_html_info(html_file_path: str) -> _HtmlInfoResult:
    with open(html_file_path, 'r') as fin:
        soup = BeautifulSoup(fin, 'lxml')  # Or 'html5lib'
        return _HtmlInfoResult(
            title=_clean_title(soup.title.string),
            is_disambiguation_page=(soup.find(id='disambigbox') is not None),
            infobox_count=len(soup.find_all(class_='infobox')))


class _FileInfoTaskArgs(NamedTuple):
    page_id: int
    html_file_path: str
    text_file_path: str


class _FileInfoTaskResult(NamedTuple):
    page_id: int
    title: str
    html_file_size: int
    text_file_size: int
    is_disambiguation_page: bool
    infobox_count: int


def _file_info_task(args: _FileInfoTaskArgs) -> _FileInfoTaskResult:
    html_info = _get_html_info(args.html_file_path)
    return _FileInfoTaskResult(
        page_id=args.page_id,
        title=html_info.title,
        html_file_size=os.path.getsize(args.html_file_path),
        text_file_size=os.path.getsize(args.text_file_path),
        is_disambiguation_page=html_info.is_disambiguation_page,
        infobox_count=html_info.infobox_count)


def _add_values_in_place(base: DefaultDict[str, int], sub: Dict[str, int]) \
        -> None:
    for (key, value) in sub.items():
        base[key] += value


def _transpose(matrix: List[List[Any]]) \
        -> Generator[Tuple[Any, ...], None, None]:
    max_column_size = max(len(row) for row in matrix)
    for i in range(max_column_size):
        yield tuple(row[i] if i < len(row) else None
                    for row in matrix)


class _MakeCategoryDatasetCatalogs(NamedTuple):
    category: str
    num_pages: int
    total_html_file_size: int
    total_text_file_size: int
    num_disambiguation_pages: int
    total_infobox_count: int
    num_pages_with_annotation: int
    num_pages_with_infobox: int
    num_attribute_types: int
    total_num_annotations: int
    attribute_counts: Dict[str, int]


def make_category_dataset_catalogs(
        dataset_dir: str, output_catalog_dir: str, category: str) \
        -> _MakeCategoryDatasetCatalogs:
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
            html_file_path=os.path.join(
                html_dir_path, dataset.make_html_file_name(page_id)),
            text_file_path=os.path.join(
                text_dir_path, dataset.make_text_file_name(page_id))))
    with Pool() as pool:
        file_info_by_page_id = {
            result.page_id: result
            for result in tqdm(pool.imap_unordered(_file_info_task,
                                                   file_info_task_args_list,
                                                   chunksize=100),
                               total=len(file_info_task_args_list))}
    catalog_file_path = os.path.join(
        output_catalog_dir, _make_file_name(category))
    with open(catalog_file_path, 'w') as fout:
        writer = util.csv_writer(fout)
        header_row = list(_FileInfoTaskResult._fields)
        header_row.append('num_annotations')
        header_row.extend(attributes)
        writer.writerow(header_row)
        num_pages = 0
        total_html_file_size = 0
        total_text_file_size = 0
        num_disambiguation_pages = 0
        total_infobox_count = 0
        num_pages_with_annotation = 0
        num_pages_with_infobox = 0
        total_num_annotations = 0
        total_attribute_counts: DefaultDict[str, int] = defaultdict(int)
        for page_id in sorted(file_info_by_page_id.keys()):
            file_info = file_info_by_page_id[page_id]
            row = list(file_info)
            annotation_info = annotation_info_by_page_id.get(page_id)
            if annotation_info:
                row.append(annotation_info.num_annotations)
                row.extend(annotation_info.attribute_counts[attribute]
                           for attribute in attributes)
            else:
                row.append(None)
                row.extend(None for unused in range(len(attributes)))
            writer.writerow(row)
            num_pages += 1
            total_html_file_size += file_info.html_file_size
            total_text_file_size += file_info.text_file_size
            total_infobox_count += file_info.infobox_count
            if annotation_info is not None \
               and annotation_info.num_annotations > 0:
                num_pages_with_annotation += 1
                total_num_annotations += annotation_info.num_annotations
                _add_values_in_place(total_attribute_counts,
                                     annotation_info.attribute_counts)
            if file_info.is_disambiguation_page:
                num_disambiguation_pages += 1
            if file_info.infobox_count > 0:
                num_pages_with_infobox += 1
    return _MakeCategoryDatasetCatalogs(
        category=category,
        num_pages=num_pages,
        total_html_file_size=total_html_file_size,
        total_text_file_size=total_text_file_size,
        num_disambiguation_pages=num_disambiguation_pages,
        total_infobox_count=total_infobox_count,
        num_pages_with_annotation=num_pages_with_annotation,
        num_pages_with_infobox=num_pages_with_infobox,
        num_attribute_types=len(attributes),
        total_num_annotations=total_num_annotations,
        attribute_counts=total_attribute_counts)


def make_dataset_catalogs(dataset_dir: str, output_catalog_dir: str) -> None:
    util.makedirs(output_catalog_dir)
    summary_rows: List[List[Any]] = []
    for category in tqdm(sorted(dataset.ALL_CATEGORIES),
                         total=len(dataset.ALL_CATEGORIES)):
        result = make_category_dataset_catalogs(
            dataset_dir, output_catalog_dir, category)
        header_row = list(_MakeCategoryDatasetCatalogs._fields)
        header_row.extend(sorted(result.attribute_counts.keys()))
        summary_rows.append(header_row)
        value_dict = result._asdict()
        value_dict['attribute_counts'] = None
        value_row = list(value_dict.values())
        value_row.extend(result.attribute_counts[attribute]
                         for attribute in sorted(result.attribute_counts))
        summary_rows.append(value_row)
    summary_file_path = os.path.join(
        output_catalog_dir, _make_file_name('summary'))
    with open(summary_file_path, 'w') as fout:
        writer = util.csv_writer(fout)
        for row in _transpose(summary_rows):
            writer.writerow(row)


def main(args: List[str]) -> None:
    parser = ArgumentParser()
    parser.add_argument('--dataset_dir',
                        type=str,
                        required=True,
                        help='Path to the dataset directory.')
    parser.add_argument('--output_catalog_dir',
                        type=str,
                        required=True,
                        help='Path to the output catalog directory.')
    flags = parser.parse_args(args)
    util.confirm(
        f'Making dataset catalogs in "{flags.output_catalog_dir}".\nContinue?')
    make_dataset_catalogs(flags.dataset_dir, flags.output_catalog_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
