#!/bin/env python3

import os
import time
import sys

import libtorrent as lt

STATE_STR = ['queued', 'checking', 'downloading metadata',
             'downloading', 'finished', 'seeding', 'allocating']

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

magnet = sys.argv[1]

session = lt.session()

status_line("listening...")
session.listen_on(6881, 6891)

params = {
    'save_path': '.',
    'storage_mode': lt.storage_mode_t.storage_mode_sparse,
}
handle = lt.add_magnet_uri(session, magnet, params)
while (handle.status().state in [0, 1, 2]):
    status_line('%s...', STATE_STR[handle.status().state])
    time.sleep(1)

torrent_info = handle.get_torrent_info()
start_mark = 0
end_mark = torrent_info.num_pieces() -1
piece_length = torrent_info.piece_length() / 1024 / 1024
num_pieces = torrent_info.num_pieces()

s = handle.status()
while (not s.is_seeding):
    if start_mark < num_pieces:
        while handle.have_piece(start_mark):
            start_mark += 1

        handle.set_piece_deadline(start_mark, 1000, 0)

    if end_mark > 0:
        while handle.have_piece(end_mark):
            end_mark -= 1

        if (num_pieces - end_mark) * piece_length < REQUIRED_FROM_END:
            handle.set_piece_deadline(end_mark, 1000, 0)

    s = handle.status()
    status_line('%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d mark: %.1f / %.1f) %s',
                s.progress * 100,
                s.download_rate / 1000,
                s.upload_rate / 1000,
                s.num_peers,
                start_mark * piece_length,
                (torrent_info.num_pieces() - end_mark) * piece_length,
                STATE_STR[s.state])
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        print('Exit requested')
        sys.exit(1)

while s.is_seeding():
    s = handle.status()
    status_line("Seeding")

    try:
        time.sleep(1)
    except KeyboardInterrupt:
        print('Exit requested')
        sys.exit(0)
