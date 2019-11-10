import shinra.inspection.annotation as a
from shinra.dataset import dataset


def test_find_html_block_tag():
    assert a._find_html_block_tag('test') is None
    assert a._find_html_block_tag('test<h1>test') == '<h1>'
    assert a._find_html_block_tag('test</h1>test') == '</h1>'
    assert a._find_html_block_tag('TEST<H1>TEST') == '<h1>'
    assert a._find_html_block_tag('TEST</H1>TEST') == '</h1>'
    assert a._find_html_block_tag('test<a>test') is None
    assert a._find_html_block_tag('test</a>test') is None


def test_braces_paired():
    assert a._braces_paired('()')
    assert a._braces_paired('(）')
    assert a._braces_paired('（)')
    assert not a._braces_paired(')(')
    assert a._braces_paired('({}<[]>)')
    assert not a._braces_paired('{[}]')


def test_is_overlapped():
    assert not a._is_overlapped(0, 1, 1, 2)
    assert a._is_overlapped(0, 2, 1, 2)
    assert not a._is_overlapped(1, 2, 0, 1)
    assert a._is_overlapped(1, 2, 0, 2)


def _make_test_annotation(annotation_id: int) -> dataset.Annotation:
    return dataset.make_annotation(
        annotation_id,
        {'page_id': 0,
         'attribute': 'test',
         'html_offset': {
             'start': {
                 'line_id': 0,
                 'offset': 0,
             },
             'end': {
                 'line_id': 0,
                 'offset': 1,
             }
         },
         'text_offset': {
             'start': {
                 'line_id': 0,
                 'offset': 0,
             },
             'end': {
                 'line_id': 0,
                 'offset': 1,
             }
         },
         })


def test_detect_overlap_annotations():
    annotation_1 = _make_test_annotation(1)
    annotation_2 = _make_test_annotation(2)
    assert list(a._detect_overlap_annotations((
        (0, 1, annotation_1),
        (1, 2, annotation_2),
    ))) == []
    assert list(a._detect_overlap_annotations((
        (0, 2, annotation_1),
        (1, 2, annotation_2),
    ))) == [a._DetectOverlapAnnotationsResult(annotation_1, annotation_2)]
