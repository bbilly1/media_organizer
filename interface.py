#!/usr/bin/env python3
""" curses interface to lunch moviesort and tvsort """

import curses
import configparser
import logging
import sys
from os import path
from time import sleep

import src.tvsort as tvsort
import src.tvsort_id as tvsort_id
import src.moviesort as moviesort
import src.db_export as db_export
import src.trailers as trailers


def get_config():
    """ read out config file and return config dict """
    # build path
    root_folder = path.dirname(sys.argv[0])
    if root_folder == '/sbin':
        # running interactive
        config_path = 'config'
    else:
        config_path = path.join(root_folder, 'config')
    # parse
    config_parser = configparser.ConfigParser()
    config_parser.read(config_path)
    # build dict
    config = {}
    config["tv_downpath"] = config_parser.get('media', 'tv_downpath')
    config["movie_downpath"] = config_parser.get('media', 'movie_downpath')
    config["sortpath"] = config_parser.get('media', 'sortpath')
    config["moviepath"] = config_parser.get('media', 'moviepath')
    config["tvpath"] = config_parser.get('media', 'tvpath')
    config["log_folder"] = config_parser.get('media', 'log_folder')
    config["movie_db_api"] = config_parser.get('media', 'movie_db_api')
    # ext
    ext_str = config_parser.get('media', 'ext')
    config["ext"] = ['.' + i for i in ext_str.split()]
    # emby
    config["emby_url"] = config_parser.get('emby', 'emby_url')
    config["emby_user_id"] = config_parser.get('emby', 'emby_user_id')
    config["emby_api_key"] = config_parser.get('emby', 'emby_api_key')
    # youtubedl_ops
    ydl_opts = dict(config_parser.items('ydl_opts'))
    # dedect string literals, is there a better way to do that?
    for key, value in ydl_opts.items():
        if value.isdigit():
            ydl_opts[key] = int(value)
        elif value.lower() in ['true', 'false']:
            ydl_opts[key] = bool(value)
    config['ydl_opts'] = ydl_opts
    return config


def get_pending_all(config):
    """ figure out what needs to be done """
    # call subfunction to collect pending
    pending_movie = moviesort.get_pending(config['movie_downpath'])
    pending_tv = tvsort.get_pending(config['tv_downpath'])
    pending_trailer = len(trailers.get_pending(config))
    pending_total = pending_movie + pending_tv + pending_trailer
    # build dict
    pending = {}
    pending['movies'] = pending_movie
    pending['tv'] = pending_tv
    pending['trailer'] = pending_trailer
    pending['total'] = pending_total
    return pending


def print_menu(stdscr, current_row_idx, menu, config, pending):
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
        moviesort.main(config)
        tvsort.main(config, tvsort_id)
        db_export.main(config)
    elif menu_item == 'Movies':
        moviesort.main(config)
    elif menu_item == 'TV shows':
        tvsort.main(config, tvsort_id)
    elif menu_item == 'DB export':
        db_export.main(config)
    elif menu_item == 'Trailer download':
        trailers.main(config)


def curses_main(stdscr, menu, config):
    """ curses main to desplay and restart the menu """
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_WHITE)
    current_row_idx = 0
    pending = get_pending_all(config)
    print_menu(stdscr, current_row_idx, menu, config, pending)
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
            print_menu(stdscr, current_row_idx, menu, config, pending)
            stdscr.refresh()
        except KeyboardInterrupt:
            # clean exit on ctrl + c
            return 'Exit'


def main():
    """ main wraps the curses menu """
    # setup
    menu = ['All', 'Movies', 'TV shows', 'DB export', 'Trailer download', 'Exit']
    config = get_config()
    log_file = path.join(config["log_folder"], 'rename.log')
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
