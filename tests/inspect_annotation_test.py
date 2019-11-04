import shinra.inspect_annotation as ia


def test_find_html_block_tag():
    assert ia._find_html_block_tag('test') is None
    assert ia._find_html_block_tag('test<h1>test') == '<h1>'
    assert ia._find_html_block_tag('test</h1>test') == '</h1>'
    assert ia._find_html_block_tag('TEST<H1>TEST') == '<h1>'
    assert ia._find_html_block_tag('TEST</H1>TEST') == '</h1>'
    assert ia._find_html_block_tag('test<a>test') is None
    assert ia._find_html_block_tag('test</a>test') is None


def test_braces_paired():
    assert ia._braces_paired('()')
    assert ia._braces_paired('(）')
    assert ia._braces_paired('（)')
    assert not ia._braces_paired(')(')
    assert ia._braces_paired('({}<[]>)')
    assert not ia._braces_paired('{[}]')
