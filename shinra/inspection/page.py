import enum
import os
import re
from collections import defaultdict
from itertools import chain
from multiprocessing import Pool
from typing import Any, DefaultDict, List, NamedTuple, Tuple

from tqdm import tqdm

from shinra import util
from shinra.content import Content, clean_html_content
from shinra.dataset import dataset


class ErrorType(enum.Enum):
    # Failure on cleaning HTML.
    CLEAN_HTML_ERROR = enum.auto()

    # The HTML content contains unescaped reserved character like < and >.
    WITH_HTML_UNESCAPED_RESERVED_CHARACTER = enum.auto()

    def __str__(self):
        # Remove the prefix of "ErrorType.".
        return self.name

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class _InspectPageTaskArgs(NamedTuple):
    page_id: int
    html_file_path: str
    text_file_path: str


class _InspectPageTaskResult(NamedTuple):
    error_type: ErrorType
    page_id: int
    error_detail: str


def _make_file_name(prefix: str) -> str:
    return f'{prefix}_page_inspection.csv'


_HTML_RESERVED_CHARACTERS = frozenset(('<', '>'))

_RE_HTML_RESERVED_CHARACTERS = re.compile(
    '|'.join(sorted(_HTML_RESERVED_CHARACTERS)))


def _contains_html_reserved_character(text: str) -> bool:
    return _RE_HTML_RESERVED_CHARACTERS.search(text) is not None


def _inspect_page_task(args: _InspectPageTaskArgs) \
        -> Tuple[_InspectPageTaskResult, ...]:
    results: List[_InspectPageTaskResult] = []
    try:
        html_content = Content.from_file(args.html_file_path)
        clean_content = clean_html_content(html_content)
        html_content_length = len(html_content.raw_content)
        clean_content_length = len(clean_content.raw_content)
        if html_content_length != clean_content_length:
            results.append(_InspectPageTaskResult(
                page_id=args.page_id,
                error_type=ErrorType.CLEAN_HTML_ERROR,
                error_detail=(
                    'Content length mismatch: '
                    + f'{html_content_length} != {clean_content_length}')))
        elif _contains_html_reserved_character(clean_content.raw_content):
            results.append(_InspectPageTaskResult(
                page_id=args.page_id,
                error_type=ErrorType.WITH_HTML_UNESCAPED_RESERVED_CHARACTER,
                error_detail=(
                    'Contains html reserved character: '
                    + ','.join(_HTML_RESERVED_CHARACTERS))))
    except Exception as e:
        results.append(_InspectPageTaskResult(
            page_id=args.page_id,
            error_type=ErrorType.CLEAN_HTML_ERROR,
            error_detail=str(e)))
    return tuple(results)


class _InspectPagesByCategoryResult(NamedTuple):
    category: str
    error_count_by_type: DefaultDict[ErrorType, int]


def inspect_pages_by_category(
        dataset_dir: str, category: str, output_dir: str) \
        -> _InspectPagesByCategoryResult:
    html_dir_path = dataset.make_html_dir_path(dataset_dir, category)
    text_dir_path = dataset.make_text_dir_path(dataset_dir, category)
    inspect_page_task_args_list = []
    for page_id in frozenset(
            dataset.get_page_id_from_file_path(file_name)
            for file_name in chain(os.listdir(os.path.join(html_dir_path)),
                                   os.listdir(os.path.join(text_dir_path)))):
        inspect_page_task_args_list.append(
            _InspectPageTaskArgs(
                page_id=page_id,
                html_file_path=os.path.join(
                    html_dir_path, dataset.make_html_file_name(page_id)),
                text_file_path=os.path.join(
                    text_dir_path, dataset.make_text_file_name(page_id))))
    output_page_file_path = os.path.join(output_dir, _make_file_name(category))
    error_count_by_type: DefaultDict[ErrorType, int] = defaultdict(int)
    with Pool() as pool:
        with open(output_page_file_path, 'w') as fout:
            writer = util.csv_writer(fout)
            writer.writerow(_InspectPageTaskResult._fields)
            for result in sorted(chain.from_iterable(tqdm(
                    pool.imap_unordered(_inspect_page_task,
                                        inspect_page_task_args_list,
                                        chunksize=10),
                    total=len(inspect_page_task_args_list)))):
                writer.writerow(result)
                error_count_by_type[result.error_type] += 1
    return _InspectPagesByCategoryResult(
        category=category,
        error_count_by_type=error_count_by_type)


def inspect_pages(dataset_dir: str, output_dir: str) -> None:
    util.makedirs(output_dir)
    results = tuple(
        inspect_pages_by_category(dataset_dir, category, output_dir)
        for category in tqdm(sorted(dataset.ALL_CATEGORIES),
                             total=len(dataset.ALL_CATEGORIES)))
    summary_file_path = os.path.join(output_dir, _make_file_name('summary'))
    with open(summary_file_path, 'w') as fout:
        writer = util.csv_writer(fout)
        header_row: List[Any] = ['category']
        header_row.extend(error_type for error_type in ErrorType)
        writer.writerow(header_row)
        for result in results:
            row: List[Any] = [result.category]
            row.extend(result.error_count_by_type[error_type]
                       for error_type in ErrorType)
            writer.writerow(row)
