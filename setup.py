# Heavily borrowed from python-boilerplate.
# https://github.com/ikasat/python-boilerplate/

import subprocess

from setuptools import Command, setup

PACKAGE_NAME = 'shinra'
VERSION = '0.1.0'


class _SimpleCommand(Command):
    user_options = []

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
        subprocess.check_call(['mypy', PACKAGE_NAME])
        subprocess.check_call(['flake8'])


def main() -> None:
    setup(
        name=PACKAGE_NAME,
        version=VERSION,
        cmdclass={
            'fmt': _FmtCommand,
            'test': _TestCommand,
            'vet': _VetCommand,
        },
    )


if __name__ == '__main__':
    main()
