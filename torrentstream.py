#!/bin/env python3

import os
import time
import sys
import argparse

import libtorrent as lt

STATE_STR = ['queued', 'checking', 'downloading metadata',
             'downloading', 'finished', 'seeding', 'allocating']

K = 1 << 10
M = 1 << 20
G = 1 << 30

REQUIRED_FROM_END = 10


def tty_size():
    return (int(i) for i in os.popen('stty size', 'r').read().split())


def status_line(format, *args):
    rows, columns = tty_size()
    data = format % args
    sys.stdout.write('\r')
    sys.stdout.write(data)
    sys.stdout.write(' ' * (columns - len(data) - 1))
    sys.stdout.flush()


def format_bytes(b):
    if b < K:
        return "%db" % (b)
    if b < M:
        return "%.1fKb" % (b / K)
    if b < G:
        return "%.1fMb" % (b / M)

    return "%.1fGb" % (b / G)


def download(uri, download_from_end=10*M):
    session = lt.session()
    status_line("listening...")
    session.listen_on(6881, 6891)
    params = {
        'save_path': '.',
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,
    }

    handle = lt.add_magnet_uri(session, uri, params)
    while (handle.status().state in [0, 1, 2]):
        status_line('%s...', STATE_STR[handle.status().state])
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print('Exit requested')
            sys.exit(1)

    torrent_info = handle.get_torrent_info()
    start_mark = 0
    end_mark = torrent_info.num_pieces() - 1
    piece_length = torrent_info.piece_length()
    num_pieces = torrent_info.num_pieces()

    s = handle.status()
    while (not s.is_seeding):
        while start_mark < num_pieces and handle.have_piece(start_mark):
            start_mark += 1

        if start_mark < num_pieces:
            handle.set_piece_deadline(start_mark, 1000, 0)

        while end_mark > 0 and handle.have_piece(end_mark):
            end_mark -= 1

        if end_mark > 0:
            if (num_pieces - end_mark) * piece_length < download_from_end:
                handle.set_piece_deadline(end_mark, 1000, 0)

        s = handle.status()
        status_line(('%s : %.2f%% complete (down: %s/s up: %s/s peers:'
                     ' %d downloaded: [ %s : %s ])'),
                    STATE_STR[s.state],
                    s.progress * 100,
                    format_bytes(s.download_rate),
                    format_bytes(s.upload_rate),
                    s.num_peers,
                    format_bytes(start_mark * piece_length),
                    format_bytes((num_pieces - end_mark - 1) * piece_length))
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print('Exit requested')
            sys.exit(1)

    while s.is_seeding:
        s = handle.status()
        status_line("Seeding...")

        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print('Exit requested')
            sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(description="Stream a torrent to disk")
    parser.add_argument('magnet_uri', metavar='magnet-uri', type=str,
                        help='magnet uri of the file to download')

    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    download(options.magnet_uri)
