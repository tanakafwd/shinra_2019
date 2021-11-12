# Heavily borrowed from python-boilerplate.
# https://github.com/ikasat/python-boilerplate/

import subprocess
from typing import Any, List

from setuptools import Command, setup

PACKAGE_NAME = 'shinra'
VERSION = '0.3.0'


class _SimpleCommand(Command):
    user_options: List[Any] = []

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        pass


class _FmtCommand(_SimpleCommand):
    def run(self) -> None:
        subprocess.call(['isort', '-y'])
        subprocess.call(['autopep8', '-ri', PACKAGE_NAME, 'tests', 'setup.py'])


class _TestCommand(_SimpleCommand):
    def run(self) -> None:
        subprocess.check_call(['pytest', '--cov', PACKAGE_NAME])


class _VetCommand(_SimpleCommand):
    def run(self) -> None:
        subprocess.check_call(
            ['mypy', PACKAGE_NAME, 'tests', 'scripts', 'setup.py'])
        subprocess.check_call(['flake8'])


def _requires_from_file(file_path: str) -> List[str]:
    with open(file_path, 'r') as fin:
        # Skip the header line.
        return fin.read().splitlines()[1:]


def main() -> None:
    setup(
        name=PACKAGE_NAME,
        version=VERSION,
        author='tanakafwd',
        description='Tools for SHINRA 2019: Wikipedia Structuring Project',
        license='MIT',
        packages=[PACKAGE_NAME],
        include_package_data=True,
        python_requires='>=3.6',
        install_requires=_requires_from_file('requirements.txt'),
        cmdclass={
            'fmt': _FmtCommand,
            'test': _TestCommand,
            'vet': _VetCommand,
        },
    )


if __name__ == '__main__':
    main()
