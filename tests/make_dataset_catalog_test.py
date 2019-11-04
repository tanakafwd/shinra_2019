import shinra.make_dataset_catalog as mdc


def test_clean_title():
    assert mdc._clean_title('伊丹空港') == '伊丹空港'
    assert mdc._clean_title('伊丹空港 - Wikipedia Dump 20171103') == '伊丹空港'


def test_transpose():
    assert tuple(mdc._transpose(((1, 2), (3, 4)))) == ((1, 3), (2, 4))
    assert tuple(mdc._transpose(((1, 2), (3, 4, 5)))) \
        == ((1, 3), (2, 4), (None, 5))
