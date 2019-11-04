#!/usr/bin/env python3
import enum
import html
import os.path
import re
import sys
import unicodedata
from argparse import ArgumentParser
from collections import defaultdict
from itertools import chain
from multiprocessing import Pool
from typing import (Any, DefaultDict, Generator, List, NamedTuple, Optional,
                    Tuple)

from tqdm import tqdm

from shinra import dataset, util
from shinra.content import Content, clean_html_content


class _InspectAnnotationsTaskArgs(NamedTuple):
    dataset_dir: str
    category: str
    page_id: int
    annotations: Tuple[dataset.Annotation, ...]


class ErrorType(enum.Enum):
    # The HTML file does not exist.
    HTML_FILE_NOT_FOUND = enum.auto()

    # The text by given offsets is not equal to the given text.
    HTML_OFFSET_MISMATCH = enum.auto()

    # The annotated text has a leading or trailing space.
    HTML_LEADING_OR_TRAILING_SPACE = enum.auto()

    # The annotated text contains a block HTML tag like h1 and h2.
    HTML_WITH_BLOCK_TAG = enum.auto()

    # The annotated text is invisible in the HTML file.
    # E.g. annotation in a script tag or in a comment.
    HTML_INVISIBLE_TEXT = enum.auto()

    # The annotated text has unpaired braces.
    HTML_UNPAIRED_BRACES = enum.auto()

    # The text file does not exist.
    TEXT_FILE_NOT_FOUND = enum.auto()

    # The text by given offsets is not equal to the given text.
    TEXT_OFFSET_MISMATCH = enum.auto()

    # The annotated text has a leading or trailing space.
    TEXT_LEADING_OR_TRAILING_SPACE = enum.auto()

    # The annotated text has unpaired braces.
    TEXT_UNPAIRED_BRACES = enum.auto()

    def __str__(self):
        # Remove the prefix of "ErrorType.".
        return self.name

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class _InspectAnnotationsTaskResult(NamedTuple):
    category: str
    error_type: ErrorType
    page_id: int
    annotation_id: Optional[int]
    error_detail: str
    annotation: Optional[dataset.Annotation]


class _InspectResult(NamedTuple):
    error_type: ErrorType
    error_detail: str
    annotation: dataset.Annotation


def _make_file_name(prefix: str) -> str:
    return f'{prefix}_annotation_inspection.csv'


# An annotation should not contain the following HTML tags.
# TODO: Confirm that an annotation with </dt> like "東京都</dt><dd>調布市" is valid or
# not.
_HTML_BLOCK_TAGS = frozenset(
    ('html',
     'body',
     'header',
     'footer',
     'h1',
     'h2',
     'h3',
     'h4',
     'h5',
     'h6',
     'dl',
     'dd',
     'dt',
     'table',
     'caption',
     'thead'
     'tbody',
     'tfoot',
     'th'
     'tr',
     'td',
     'img',
     # TODO: Add more.
     ))

_RE_HTML_BLOCK_TAGS = re.compile(
    r'</?\s*(?:' + '|'.join(sorted(_HTML_BLOCK_TAGS)) + r'\s*)>')


def _find_html_block_tag(html_text: str) -> Optional[str]:
    m = _RE_HTML_BLOCK_TAGS.search(html_text.lower())
    return None if m is None else m.group(0)


_BRACE_PAIRS = (
    ('(', ')'),
    ('[', ']'),
    ('{', '}'),
    ('<', '>'),
    ('「', '」'),
    ('『', '』'))

_OPEN_BRACE_TO_CLOSE = {
    open_brace: close_brace for (open_brace, close_brace) in _BRACE_PAIRS}

_CLOSE_BRACE_TO_OPEN = {
    close_brace: open_brace for (open_brace, close_brace) in _BRACE_PAIRS}


def _braces_paired(text: str) -> bool:
    normalized_text = unicodedata.normalize('NFKC', text)
    braces_stack = []
    for ch in normalized_text:
        if ch in _OPEN_BRACE_TO_CLOSE:
            braces_stack.append(ch)
        elif ch in _CLOSE_BRACE_TO_OPEN:
            if not braces_stack:
                # No corresponding open brace.
                return False
            last_open_brace = braces_stack.pop()
            if _CLOSE_BRACE_TO_OPEN[ch] != last_open_brace:
                # No corresponding open brace.
                return False
    if braces_stack:
        # No corresponding close brace.
        return False
    return True


def _check_html_text(
        content: Content, annotations: Tuple[dataset.Annotation, ...]) \
        -> Generator[_InspectResult, None, None]:
    clean_content = clean_html_content(content)
    for annotation in annotations:
        offset = annotation.html_offset
        if offset is not None and offset.text is not None:
            text = content.get_text(
                offset.start.line_id,
                offset.start.offset,
                offset.end.line_id,
                offset.end.offset)
            if text != offset.text:
                yield _InspectResult(
                    error_type=ErrorType.HTML_OFFSET_MISMATCH,
                    error_detail=f'"{offset.text}" != "{text}"',
                    annotation=annotation)
                continue
            stripped_text = offset.text.strip()
            if stripped_text != text:
                yield _InspectResult(
                    error_type=ErrorType.HTML_LEADING_OR_TRAILING_SPACE,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            block_html_tag = _find_html_block_tag(text)
            if block_html_tag:
                yield _InspectResult(
                    error_type=ErrorType.HTML_WITH_BLOCK_TAG,
                    error_detail=f'{block_html_tag} in "{offset.text}"',
                    annotation=annotation)
                continue
            clean_text = clean_content.get_text(
                offset.start.line_id,
                offset.start.offset,
                offset.end.line_id,
                offset.end.offset)
            stripped_clean_text = clean_text.strip()
            if not stripped_clean_text:
                yield _InspectResult(
                    error_type=ErrorType.HTML_INVISIBLE_TEXT,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            if stripped_clean_text != clean_text:
                yield _InspectResult(
                    # TODO: Cosider using another error type.
                    error_type=ErrorType.HTML_LEADING_OR_TRAILING_SPACE,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            unescaped_text = html.unescape(clean_text)
            stripped_unescaped_text = unescaped_text.strip()
            if stripped_unescaped_text != unescaped_text:
                yield _InspectResult(
                    # TODO: Cosider using another error type.
                    error_type=ErrorType.HTML_LEADING_OR_TRAILING_SPACE,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            if not _braces_paired(unescaped_text):
                yield _InspectResult(
                    error_type=ErrorType.HTML_UNPAIRED_BRACES,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            # TODO: Also output a suggestion to modify the annotation.
            # TODO: Detect tokenization mismatch.


def _check_text_text(
        content: Content, annotations: Tuple[dataset.Annotation, ...]) \
        -> Generator[_InspectResult, None, None]:
    for annotation in annotations:
        offset = annotation.text_offset
        if offset is not None and offset.text is not None:
            text = content.get_text(
                offset.start.line_id,
                offset.start.offset,
                offset.end.line_id,
                offset.end.offset)
            if text != offset.text:
                yield _InspectResult(
                    error_type=ErrorType.TEXT_OFFSET_MISMATCH,
                    error_detail=f'"{offset.text}" != "{text}"',
                    annotation=annotation)
                continue
            stripped_text = offset.text.strip()
            if stripped_text != text:
                yield _InspectResult(
                    error_type=ErrorType.TEXT_LEADING_OR_TRAILING_SPACE,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            if not _braces_paired(offset.text):
                yield _InspectResult(
                    error_type=ErrorType.TEXT_UNPAIRED_BRACES,
                    error_detail=f'"{offset.text}"',
                    annotation=annotation)
                continue
            # TODO: Also output a suggestion to modify the annotation.
            # TODO: Detect tokenization mismatch.


def _inspect_annotations_task(args: _InspectAnnotationsTaskArgs) \
        -> Tuple[_InspectAnnotationsTaskResult, ...]:
    results: List[_InspectAnnotationsTaskResult] = []
    html_file_path = os.path.join(
        dataset.make_html_dir_path(args.dataset_dir, args.category),
        dataset.make_html_file_name(args.page_id))
    # TODO: Clean inspection logic. For example, extract checks for both HTML
    # and text.
    if os.path.exists(html_file_path):
        html_content = Content.from_file(html_file_path)
        for result in _check_html_text(html_content, args.annotations):
            results.append(_InspectAnnotationsTaskResult(
                category=args.category,
                error_type=result.error_type,
                page_id=args.page_id,
                annotation_id=result.annotation.annotation_id,
                error_detail=result.error_detail,
                annotation=result.annotation))
    else:
        results.append(_InspectAnnotationsTaskResult(
            category=args.category,
            error_type=ErrorType.HTML_FILE_NOT_FOUND,
            page_id=args.page_id,
            annotation_id=None,
            error_detail=f'HTML file not found: "{html_file_path}"',
            annotation=None))
    text_file_path = os.path.join(
        dataset.make_text_dir_path(args.dataset_dir, args.category),
        dataset.make_text_file_name(args.page_id))
    if os.path.exists(text_file_path):
        text_content = Content.from_file(text_file_path)
        for result in _check_text_text(text_content, args.annotations):
            results.append(_InspectAnnotationsTaskResult(
                category=args.category,
                error_type=result.error_type,
                page_id=args.page_id,
                annotation_id=result.annotation.annotation_id,
                error_detail=result.error_detail,
                annotation=result.annotation))
    else:
        results.append(_InspectAnnotationsTaskResult(
            category=args.category,
            error_type=ErrorType.TEXT_FILE_NOT_FOUND,
            page_id=args.page_id,
            annotation_id=None,
            error_detail=f'TEXT file not found: "{text_file_path}"',
            annotation=None))
    return tuple(results)


class _InspectAnnotationsByCategoryResult(NamedTuple):
    category: str
    error_count_by_type: DefaultDict[ErrorType, int]


def inspect_annotations_by_category(
        dataset_dir: str, category: str, output_dir: str) \
        -> _InspectAnnotationsByCategoryResult:
    annotation_file_path = os.path.join(
        dataset.make_annotation_dir_path(dataset_dir), f'{category}_dist.json')
    annotations_by_page_id = dataset.read_annotations_by_page_id(
        annotation_file_path)
    inspect_annotations_task_args_list = tuple(
        _InspectAnnotationsTaskArgs(
            dataset_dir=dataset_dir,
            category=category,
            page_id=page_id,
            annotations=tuple(annotations))
        for (page_id, annotations) in annotations_by_page_id.items())
    output_inspection_file_path = os.path.join(
        output_dir, _make_file_name(category))
    error_count_by_type: DefaultDict[ErrorType, int] = defaultdict(int)
    with Pool() as pool:
        with open(output_inspection_file_path, 'w') as fout:
            writer = util.csv_writer(fout)
            writer.writerow(_InspectAnnotationsTaskResult._fields)
            for result in sorted(chain.from_iterable(tqdm(
                pool.imap_unordered(_inspect_annotations_task,
                                    inspect_annotations_task_args_list,
                                    chunksize=10),
                    total=len(inspect_annotations_task_args_list)))):
                writer.writerow(result)
                error_count_by_type[result.error_type] += 1
    return _InspectAnnotationsByCategoryResult(
        category=category,
        error_count_by_type=error_count_by_type)


def inspect_annotations(dataset_dir: str, output_dir: str) -> None:
    util.makedirs(output_dir)
    results = tuple(
        inspect_annotations_by_category(dataset_dir, category, output_dir)
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
    inspect_annotations(flags.dataset_dir, flags.output_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
