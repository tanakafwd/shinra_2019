import bisect
from html.parser import HTMLParser
from typing import Generator, List, Optional, Tuple


class Content:
    def __init__(self, raw_content: str) -> None:
        assert raw_content
        self._line_offsets = tuple(self._gen_line_offsets(raw_content))
        self._raw_content = raw_content

    @property
    def raw_content(self) -> str:
        return self._raw_content

    @staticmethod
    def _gen_line_offsets(raw_content: str) -> Generator[int, None, None]:
        offset = 0
        # Do not use raw_content.splitlines(keepends=True) because it also
        # splits a string into lines by Unicode line separators such as \u2028
        # and \u2029.
        # https://docs.python.org/3.6/library/stdtypes.html#str.splitlines
        for line in raw_content.split('\n'):
            yield offset
            offset += len(line) + 1  # +1 for '\n'.
        yield offset

    def get_char_offset(self, line_id: int, offset: int) -> int:
        return self._line_offsets[line_id] + offset

    def get_line_offset(self, char_offset: int) -> Tuple[int, int]:
        assert char_offset >= 0
        i = bisect.bisect_right(self._line_offsets, char_offset)
        line_id = i - 1
        offset = char_offset - self._line_offsets[line_id]
        return (line_id, offset)

    def get_text(self, start_line_id: int, start_offset: int, end_line_id: int,
                 end_offset: int) -> str:
        # (start_line_id, offset) are inclusive whereas (end_line_id, offset)
        # are exclusive.
        start_char_offset = self.get_char_offset(start_line_id, start_offset)
        end_char_offset = self.get_char_offset(end_line_id, end_offset)
        return self.get_text_by_char_offset(start_char_offset, end_char_offset)

    def get_text_by_char_offset(
            self, start_char_offset: int, end_char_offset: int) -> str:
        # start_char_offset is inclusive whereas end_char_offset is exclusive.
        return self._raw_content[start_char_offset:end_char_offset]

    def get_last_line_offset(self) -> Tuple[int, int]:
        return self.get_line_offset(len(self._raw_content))

    @classmethod
    def from_file(cls, file_path: str) -> 'Content':
        with open(file_path, 'r') as fin:
            return cls(fin.read())


class _HtmlCleaner(HTMLParser):
    """Remove start/end tags and comments from a given HTML string."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)

    def clean(self, content: Content) -> str:
        self._script_tag_stack: List[str] = []
        self._content = content
        self._cleaned_content = list(content.raw_content)
        self.feed(content.raw_content)
        return ''.join(self._cleaned_content)

    def handle_decl(self, decl: str) -> None:
        (tag_start_line_id, tag_start_offset) = self._get_position()
        char_offset = self._content.get_char_offset(tag_start_line_id,
                                                    tag_start_offset)
        # 3 is len('<!') + len('>').
        self._set_blank(char_offset, char_offset + len(decl) + 3)

    def handle_starttag(
            self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self._clear_tag()
        if self._is_script_tag(tag):
            self._script_tag_stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, str]]) \
            -> None:
        self._clear_tag()

    def handle_endtag(self, tag: str) -> None:
        self._clear_tag()
        if self._is_script_tag(tag):
            self._script_tag_stack.pop()

    def _clear_tag(self) -> None:
        (tag_start_line_id, tag_start_offset) = self._get_position()
        char_offset = self._content.get_char_offset(tag_start_line_id,
                                                    tag_start_offset)
        index = self._content.raw_content.find('>', char_offset)
        self._set_blank(char_offset, index + 1)

    def handle_comment(self, data: str) -> None:
        (tag_start_line_id, tag_start_offset) = self._get_position()
        char_offset = self._content.get_char_offset(tag_start_line_id,
                                                    tag_start_offset)
        # 7 is len('<!--') + len('-->').
        self._set_blank(char_offset, char_offset + len(data) + 7)

    def handle_data(self, data: str) -> None:
        if self._script_tag_stack:
            # Remove data within a script tag.
            (data_start_line_id, data_start_offset) = self._get_position()
            char_offset = self._content.get_char_offset(data_start_line_id,
                                                        data_start_offset)
            self._set_blank(char_offset, char_offset + len(data))

    def handle_entityref(self, name: str) -> None:
        pass

    def handle_charref(self, name: str) -> None:
        pass

    def _get_position(self) -> Tuple[int, int]:
        (line_id, offset) = self.getpos()
        return (line_id - 1, offset)

    def _set_blank(self, start_char_offset: int, end_char_offset: int) -> None:
        # start_char_offset is inclusive whereas end_char_offset is exclusive.
        for i in range(start_char_offset, end_char_offset):
            # Do not overwrite newline characters.
            if not self._is_newline(self._cleaned_content[i]):
                self._cleaned_content[i] = ' '

    @staticmethod
    def _is_newline(char: str) -> bool:
        return char == '\n'

    @staticmethod
    def _is_script_tag(tag: str) -> bool:
        return tag.strip().lower() == 'script'


def clean_html(content: Content) -> str:
    return _HtmlCleaner().clean(content)


def clean_html_content(content: Content) -> Content:
    return Content(clean_html(content))
