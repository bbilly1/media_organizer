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


class Interface():
    """ creating and removing the menu """

    CONFIG = get_config()
    log_folder = CONFIG['media']['log_folder']
    log_file = path.join(log_folder, 'rename.log')
    logging.basicConfig(
        filename=log_file, level=logging.INFO, format='%(asctime)s:%(message)s'
    )

    def __init__(self):
        self.menu = self.build_menu()
        self.stdscr = None
        self.menu_item = 0
        self.pending = self.get_pending_all()

    def get_pending_all(self):
        """ figure out what needs to be done """
        # call subfunction to collect pending
        pending = {}
        pending_movie = moviesort.MovieHandler().pending
        pending_tv = tvsort.TvHandler().pending
        pending['movies'] = pending_movie
        pending['tv'] = pending_tv
        # based on config key
        if 'emby' in self.CONFIG.keys():
            pending_trailer = len(trailers.TrailerHandler().pending)
            pending_movie_fix = len(id_fix.MovieNameFix().pending)
            pending['trailer'] = pending_trailer
            pending['movie_fix'] = pending_movie_fix
            pending_total = (pending_movie + pending_tv +
                             pending_trailer + pending_movie_fix)
        else:
            pending_total = pending_movie + pending_tv
        pending['total'] = pending_total
        return pending

    def build_menu(self):
        """ build the menu based on availabe keys in config file """
        menu = ['All', 'Movies', 'TV shows', 'Trailer download',
                'Fix Movie Names', 'DB export', 'Exit']
        config_keys = self.CONFIG.keys()
        if 'emby' not in config_keys:
            menu.remove('Fix Movie Names')
            menu.remove('DB export')
        if 'ydl_opts' not in config_keys:
            menu.remove('Trailer download')
        return menu

    def create_interface(self):
        """ create the main loop for curses.wrapper """
        while True:
            menu_item = curses.wrapper(self.curses_main)
            if menu_item != 'Exit':
                self.sel_handler(menu_item)
                sleep(3)
                self.pending = self.get_pending_all()
            else:
                return

    def curses_main(self, stdscr):
        """ curses main to desplay and restart the menu """
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_WHITE)
        current_row_idx = 0
        self.print_menu(current_row_idx)
        # endless loop
        while True:
            # wait for exit signal
            try:
                key = stdscr.getch()
                stdscr.clear()
                # react to kee press
                last = len(self.menu) - 1
                if key == curses.KEY_UP and current_row_idx > 0:
                    current_row_idx -= 1
                elif key == curses.KEY_DOWN and current_row_idx < last:
                    current_row_idx += 1
                elif key == curses.KEY_ENTER or key in [10, 13]:
                    menu_item = self.menu[current_row_idx]
                    stdscr.addstr(0, 0, f'start task: {menu_item}')
                    stdscr.refresh()
                    sleep(1)
                    # exit curses and do something
                    return menu_item
                elif key == ord('q'):
                    return 'Exit'
                elif key == ord('r'):
                    stdscr.addstr(0, 0, 'refreshing pending')
                    self.pending = self.get_pending_all()
                    stdscr.refresh()
                    sleep(1)
                # print
                self.print_menu(current_row_idx)
                stdscr.refresh()
            except KeyboardInterrupt:
                # clean exit on ctrl + c
                return 'Exit'

    @staticmethod
    def sel_handler(menu_item):
        """ lunch scripts from here based on selection """
        if menu_item == 'All':
            moviesort.main()
            tvsort.main()
            trailers.main()
            id_fix.main()
            db_export.main()
        elif menu_item == 'Movies':
            moviesort.main()
        elif menu_item == 'TV shows':
            tvsort.main()
        elif menu_item == 'Trailer download':
            trailers.main()
        elif menu_item == 'Fix Movie Names':
            id_fix.main()
        elif menu_item == 'DB export':
            db_export.main()

    def print_menu(self, current_row_idx):
        """ print menu with populated pending count """
        # build stdscr
        menu = self.menu
        h, w = self.stdscr.getmaxyx()
        longest = len(max(menu))
        x = w // 2 - longest
        self.stdscr.clear()
        # help
        self.stdscr.addstr(h - 1, x, 'q: quit, r: refresh')
        # loop through menu items
        for idx, row in enumerate(menu):
            # menu items count
            if row == 'All':
                pending_count = self.pending['total']
            elif row == 'Movies':
                pending_count = self.pending['movies']
            elif row == 'TV shows':
                pending_count = self.pending['tv']
            elif row == 'Trailer download':
                pending_count = self.pending['trailer']
            elif row == 'Fix Movie Names':
                pending_count = self.pending['movie_fix']
            else:
                pending_count = ' '
            # center whole
            y = h // 2 - len(menu) + idx
            # print string to menu
            text = f'[{pending_count}] {row}'
            if idx == current_row_idx:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y, x, text)
                self.stdscr.attroff(curses.color_pair(1))
            else:
                self.stdscr.addstr(y, x, text)
        # load
        self.stdscr.refresh()


def main():
    """ main wraps the curses menu """
    # setup
    window = Interface()
    window.create_interface()


# start here
if __name__ == "__main__":
    main()
