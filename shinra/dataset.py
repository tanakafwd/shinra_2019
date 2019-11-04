import json
import os.path
from collections import defaultdict
from typing import Any, Dict, List, NamedTuple, Optional

DATASET_FILE_NAMES = {
    # File name and md5 digest of its content.
    'JP-5_20190712.zip': 'd278548f38abb9778d4d24e78487b4fd',
    'JP-30_20190712.zip': '6d4db54cb2a3d047779eb5bda5ac6c49',
}

JP5_CATEGORIES = frozenset(
    ('Airport', 'City', 'Company', 'Compound', 'Person'))

JP30_LOCATION_CATEGORIES = frozenset((
    'Bay',
    'Continental_Region',
    'Country',
    'Domestic_Region',
    'GPE_Other',
    'Geological_Region_Other',
    'Island',
    'Lake',
    'Location_Other',
    'Mountain',
    'Province',
    'River',
    'Sea',
    'Spa'))

JP30_ORGANIZATION_CATEGORIES = frozenset((
    'Cabinet',
    'Company_Group',
    'Ethnic_Group_Other',
    'Family',
    'Government',
    'International_Organization',
    'Military',
    'Nationality',
    'Nonprofit_Organization',
    'Organization_Other',
    'Political_Organization_Other',
    'Political_Party',
    'Show_Organization',
    'Sports_Federation',
    'Sports_League',
    'Sports_Team'))

ALL_CATEGORIES = JP5_CATEGORIES.union(
    JP30_LOCATION_CATEGORIES).union(JP30_ORGANIZATION_CATEGORIES)


def get_page_id_from_file_path(file_path: str) -> int:
    return int(os.path.basename(file_path).split('.')[0])


def get_category_from_dir_path(dir_path: str) -> Optional[str]:
    (head, tail) = os.path.split(dir_path)
    while True:
        if tail in ALL_CATEGORIES:
            return tail
        if not head or not tail:
            break
        (head, tail) = os.path.split(head)
    return None


def make_annotation_dir_path(dataset_dir: str) -> str:
    return os.path.join(dataset_dir, 'annotation')


def make_html_dir_path(dataset_dir: str, category: str) -> str:
    return os.path.join(dataset_dir, 'HTML', category)


def make_html_file_name(page_id: int) -> str:
    return f'{page_id}.html'


def make_text_dir_path(dataset_dir: str, category: str) -> str:
    return os.path.join(dataset_dir, 'PLAIN', category)


def make_text_file_name(page_id: int) -> str:
    return f'{page_id}.txt'


class LineOffset(NamedTuple):
    line_id: int
    offset: int


class Offset(NamedTuple):
    start: Optional[LineOffset]
    end: Optional[LineOffset]
    text: Optional[str]


class Annotation(NamedTuple):
    annotation_id: int
    page_id: int
    title: Optional[str]
    ene: Optional[str]
    attribute: str
    html_offset: Optional[Offset]
    text_offset: Optional[Offset]


def make_line_offset(data: Optional[Any]) -> Optional[LineOffset]:
    if data is None:
        return None
    return LineOffset(
        line_id=data.get('line_id'),
        offset=data.get('offset'))


def make_offset(data: Optional[Any]) -> Optional[Offset]:
    if data is None:
        return None
    return Offset(
        start=make_line_offset(data.get('start')),
        end=make_line_offset(data.get('end')),
        text=data.get('text'))


def make_annotation(annotation_id: int, data: Dict[str, Any]) -> Annotation:
    return Annotation(
        annotation_id=annotation_id,
        page_id=int(data['page_id']),
        title=data.get('title'),
        ene=data.get('ene'),
        attribute=data['attribute'],
        html_offset=make_offset(data.get('html_offset')),
        text_offset=make_offset(data.get('text_offset')))


def parse_annotation_line(annotation_id: int, line: str) -> Annotation:
    return make_annotation(annotation_id, json.loads(line))


def read_annotations_by_page_id(annotation_file_path: str) \
        -> Dict[int, List[Annotation]]:
    annotations_by_page_id: Dict[int, List[Annotation]] = defaultdict(list)
    with open(annotation_file_path, 'r') as fin:
        for (annotation_id, line) in enumerate(fin):
            # Use a line id in the file as annotation id.
            annotation = parse_annotation_line(annotation_id, line)
            annotations_by_page_id[annotation.page_id].append(annotation)
    return annotations_by_page_id
