#!/usr/bin/env python3
""" curses interface to lunch moviesort and tvsort """

import curses
import logging
from os import path
from time import sleep

from src.config import get_config

import src.tvsort as tvsort
import src.moviesort as moviesort
import src.db_export as db_export
import src.trailers as trailers
import src.id_fix as id_fix


def get_pending_all(config):
    """ figure out what needs to be done """
    # call subfunction to collect pending
    pending_movie = moviesort.MovieHandler().pending
    pending_tv = tvsort.TvHandler().pending
    pending_trailer = len(trailers.TrailerHandler().pending)
    pending_movie_fix = len(id_fix.get_pending(config))
    pending_total = pending_movie + pending_tv + pending_trailer + pending_movie_fix
    # build dict
    pending = {}
    pending['movies'] = pending_movie
    pending['tv'] = pending_tv
    pending['trailer'] = pending_trailer
    pending['movie_fix'] = pending_movie_fix
    pending['total'] = pending_total
    return pending


def print_menu(stdscr, current_row_idx, menu, pending):
    """ print menu with populated pending count """
    # build stdscr
    h, w = stdscr.getmaxyx()
    longest = len(max(menu))
    x = w // 2 - longest
    stdscr.clear()
    # loop through menu items
    for idx, row in enumerate(menu):
        # menu items count
        if row == 'All':
            pending_count = pending['total']
        elif row == 'Movies':
            pending_count = pending['movies']
        elif row == 'TV shows':
            pending_count = pending['tv']
        elif row == 'Trailer download':
            pending_count = pending['trailer']
        elif row == 'Fix Movie Names':
            pending_count = pending['movie_fix']
        else:
            pending_count = ' '
        # center whole
        y = h // 2 - len(menu) + idx
        # print string to menu
        text = f'[{pending_count}] {row}'
        if idx == current_row_idx:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(y, x, text)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y, x, text)
    # load
    stdscr.refresh()


def sel_handler(menu_item, config):
    """ lunch scripts from here based on selection """
    if menu_item == 'All':
        moviesort.main()
        tvsort.main()
        db_export.main()
        trailers.main()
        id_fix.main(config)
    elif menu_item == 'Movies':
        moviesort.main()
    elif menu_item == 'TV shows':
        tvsort.main()
    elif menu_item == 'DB export':
        db_export.main()
    elif menu_item == 'Trailer download':
        trailers.main()
    elif menu_item == 'Fix Movie Names':
        id_fix.main(config)


def curses_main(stdscr, menu, config):
    """ curses main to desplay and restart the menu """
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_WHITE)
    current_row_idx = 0
    pending = get_pending_all(config)
    print_menu(stdscr, current_row_idx, menu, pending)
    # endless loop
    while True:
        # wait for exit signal
        try:
            key = stdscr.getch()
            stdscr.clear()
            # react to kee press
            if key == curses.KEY_UP and current_row_idx > 0:
                current_row_idx -= 1
            elif key == curses.KEY_DOWN and current_row_idx < len(menu) - 1:
                current_row_idx += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                menu_item = menu[current_row_idx]
                stdscr.addstr(0, 0, f'start task: {menu_item}')
                stdscr.refresh()
                sleep(1)
                # exit curses and do something
                return menu_item
            # print
            print_menu(stdscr, current_row_idx, menu, pending)
            stdscr.refresh()
        except KeyboardInterrupt:
            # clean exit on ctrl + c
            return 'Exit'


def main():
    """ main wraps the curses menu """
    # setup
    menu = ['All', 'Movies', 'TV shows', 'DB export', 'Trailer download', 'Fix Movie Names', 'Exit']
    config = get_config()
    log_folder = config['media']['log_folder']
    log_file = path.join(log_folder, 'rename.log')
    logging.basicConfig(filename=log_file,level=logging.INFO,format='%(asctime)s:%(message)s')
    # endless loop
    while True:
        pending = get_pending_all(config)
        if not pending:
            return
        menu_item = curses.wrapper(curses_main, menu, config)
        if menu_item == 'Exit':
            return
        else:
            sel_handler(menu_item, config)
            sleep(3)


# start here
if __name__ == "__main__":
    main()
