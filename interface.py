#!/usr/bin/env python3
""" curses interface to lunch moviesort and tvsort """

import curses
import logging
from os import path
from time import sleep

from src.config import get_config

from src import tvsort
from src import moviesort
from src import db_export
from src import trailers
from src import id_fix


class Interface:
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

    def center_message(self, message):
        """ center message in stdscr """
        max_h, max_w = self.stdscr.getmaxyx()
        h = max_h // 2
        w = max_w // 2 - len(message) // 2
        return h, w

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
                    message = f'start task: {menu_item}'
                    h, w = self.center_message(message)
                    stdscr.addstr(h, w, message)
                    stdscr.refresh()
                    sleep(1)
                    # exit curses and do something
                    return menu_item
                elif key == ord('q'):
                    return 'Exit'
                elif key == ord('r'):
                    message = 'refreshing pending'
                    h, w = self.center_message(message)
                    stdscr.addstr(h, w, message)
                    self.pending = self.get_pending_all()
                    stdscr.refresh()
                    sleep(1)
                # print
                self.print_menu(current_row_idx)
                stdscr.refresh()
            except KeyboardInterrupt:
                # clean exit on ctrl + c
                return 'Exit'

    def sel_handler(self, menu_item):
        """ lunch scripts from here based on selection """
        if menu_item == 'All':
            moviesort.main()
            tvsort.main()
            if 'ydl_opts' in self.CONFIG.keys():
                trailers.main()
            if 'emby' in self.CONFIG.keys():
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
        self.stdscr.clear()
        max_h, max_w = self.stdscr.getmaxyx()
        # menu strings
        message = 'github.com/bbilly1/media_organizer'
        _, w = self.center_message(message)
        self.stdscr.addstr(max_h - 1, w, message)
        message = 'q: quit, r: refresh'
        _, w = self.center_message(message)
        self.stdscr.addstr(max_h - 2, w, message)
        # build stdscr
        longest = len(max(self.menu))
        x = max_w // 2 - longest // 2 - 2
        first_menu = max_h // 2 - len(self.menu) // 2
        self.stdscr.addstr(first_menu - 2, x, 'Media Organizer')
        # loop through menu items
        for idx, row in enumerate(self.menu):
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
            y = first_menu + idx
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
