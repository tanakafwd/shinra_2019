import shinra.dataset as d


def test_get_page_id_from_file_path():
    assert d.get_page_id_from_file_path('12345.html') == 12345
    assert d.get_page_id_from_file_path('12345.txt') == 12345
    assert d.get_page_id_from_file_path('12345.json.gz') == 12345
    assert d.get_page_id_from_file_path('/tmp/12345.html') == 12345
    assert d.get_page_id_from_file_path('/tmp/12345.txt') == 12345
    assert d.get_page_id_from_file_path('/tmp/12345.json.gz') == 12345


def test_get_category_from_dir_path():
    assert d.get_category_from_dir_path('') is None
    assert d.get_category_from_dir_path('/tmp/Airport') == 'Airport'
    assert d.get_category_from_dir_path('/tmp/Unknown') is None
    assert d.get_category_from_dir_path('/tmp/Airport/HTML') == 'Airport'
    assert d.get_category_from_dir_path('/tmp/Unknown/HTML') is None
    assert d.get_category_from_dir_path('tmp/Airport') == 'Airport'
    assert d.get_category_from_dir_path('tmp/Unknown') is None
    assert d.get_category_from_dir_path('tmp/Airport/HTML') == 'Airport'
    assert d.get_category_from_dir_path('tmp/Unknown/HTML') is None
