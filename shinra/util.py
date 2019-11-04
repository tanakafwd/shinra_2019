import csv
import hashlib
import os
import sys


def confirm(message: str) -> None:
    response = input(message + ' [y/N]: ').lower()
    if response in ('y', 'yes'):
        return
    print('exit')
    sys.exit(1)


def makedirs(dir_path: str) -> None:
    # $ mkdir -p "${dir_path}"
    try:
        os.makedirs(dir_path)
    except FileExistsError:
        pass


def md5(file_path: str) -> str:
    h = hashlib.new('md5')
    block_size = h.block_size * 0x1000
    with open(file_path, 'rb') as fin:
        data = fin.read(block_size)
        while data:
            h.update(data)
            data = fin.read(block_size)
    return h.hexdigest().lower()


# Allow to read huge CSV files.
csv.field_size_limit(1048576)


def csv_reader(fin):
    return csv.reader(fin)


def csv_writer(fout):
    return csv.writer(fout, lineterminator='\n')
