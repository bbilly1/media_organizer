""" handles moving tv downloads """

import os
import subprocess
from time import sleep


def get_pending(tv_downpath):
    """ return how many shows are pending """
    pending = len(os.listdir(tv_downpath))
    return pending


def move_to_sort(tv_downpath, sortpath, ext):
    """ move tv files to sortpath """
    for dirpath, _, filenames in os.walk(tv_downpath):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            _, extenstion = os.path.splitext(path)
            f_size = os.stat(path).st_size
            if extenstion.lower() in ext and 'sample' not in filename and f_size > 50000000:
                move_to = os.path.join(sortpath, filename)
                os.rename(path, move_to)
    if os.listdir(sortpath):
        return True
    else:
        return False


def move_to_archive(sortpath, tvpath):
    """ moves the renamed files to the archive """
    print()
    for dirpath, _, filenames in os.walk(sortpath):
        for show in sorted(filenames):
            print(show)
    input('\ncontinue?')
    # apply
    for dirpath, _, filenames in os.walk(sortpath):
        for show in filenames:
            old_file = os.path.join(sortpath, dirpath, show)
            show_name = dirpath.split('/')[-2]
            season_name = dirpath.split('/')[-1]
            new_folder = os.path.join(tvpath, show_name, season_name)
            new_file = os.path.join(new_folder, show)
            os.makedirs(new_folder, exist_ok=True)
            os.rename(old_file, new_file)


def clean_up(sortpath, tv_downpath):
    """ clean up download and sort folder """
    to_clean_list = os.listdir(sortpath)
    for to_clean in to_clean_list:
        to_trash = os.path.join(sortpath, to_clean)
        subprocess.call(["trash", to_trash])
    to_clean_list = os.listdir(tv_downpath)
    for to_clean in to_clean_list:
        to_trash = os.path.join(tv_downpath, to_clean)
        subprocess.call(["trash", to_trash])


def main(config, tvsort_id):
    """ main function to sort tv shows """
    # parse config
    tv_downpath = config['tv_downpath']
    tvpath = config['tvpath']
    sortpath = config['sortpath']
    ext = config['ext']
    # stop here if nothing to do
    pending = get_pending(tv_downpath)
    if not pending:
        print('no tv shows to sort')
        sleep(2)
        return
    
    # move files
    to_sort = move_to_sort(tv_downpath, sortpath, ext)
    if to_sort:
        renamed = tvsort_id.episode_rename(config)
    if renamed:
        move_to_archive(sortpath, tvpath)
        clean_up(sortpath, tv_downpath)
