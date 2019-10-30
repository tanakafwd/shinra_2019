import json
import os.path
from collections import defaultdict
from typing import Any, Dict, List, Optional

DATASET_FILE_NAMES = {
    # File name and md5 digest of its content.
    'JP-5_20190712.zip': 'd278548f38abb9778d4d24e78487b4fd',
    'JP-30_20190712.zip': '6d4db54cb2a3d047779eb5bda5ac6c49',
}

JP5_CATEGORIES = frozenset(
    ('Airport', 'City', 'Company', 'Compound', 'Person'))

JP30_CATEGORIES = frozenset(
    ('Bay', 'Cabinet', 'Company_Group', 'Continental_Region', 'Country',
     'Domestic_Region', 'Ethnic_Group_Other', 'Family',
     'Geological_Region_Other', 'Government', 'GPE_Other',
     'International_Organization', 'Island', 'Lake', 'Location_Other',
     'Military', 'Mountain', 'Nationality', 'Nonprofit_Organization',
     'Organization_Other', 'Political_Organization_Other', 'Political_Party',
     'Province', 'River', 'Sea', 'Show_Organization', 'Spa',
     'Sports_Federation', 'Sports_League', 'Sports_Team'))

ALL_CATEGORIES = JP5_CATEGORIES.union(JP30_CATEGORIES)


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


def make_text_dir_path(dataset_dir: str, category: str) -> str:
    return os.path.join(dataset_dir, 'PLAIN', category)


def parse_annotation_line(line: str) -> Dict[str, Any]:
    return json.loads(line)


def read_annotation_lines_by_page_id(annotation_file_path: str) \
        -> Dict[int, List[str]]:
    lines_by_page_id: Dict[int, List[str]] = defaultdict(list)
    with open(annotation_file_path, 'r') as fin:
        for line in fin:
            page_id = int(parse_annotation_line(line)['page_id'])
            lines_by_page_id[page_id].append(line)
    return lines_by_page_id
