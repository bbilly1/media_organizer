""" looks for movies wrongly identified in emby """

import os
import re
import requests

from time import sleep


def get_emby_list(config):
    """ get current emby movie list """
    emby_url = config['emby_url']
    emby_user_id = config['emby_user_id']
    emby_api_key = config['emby_api_key']

    url = (emby_url + '/Users/' + emby_user_id + '/Items?api_key=' + emby_api_key + 
        '&Recursive=True&IncludeItemTypes=Movie&Fields=Path,PremiereDate')
    r_emby = requests.get(url).json()
    movie_list = r_emby['Items']
    return movie_list


def compare_list(movie_list):
    """ compare the movie_list and look for wong ids """
    errors_list = []
    for movie in movie_list:
        # from file name
        file_name = os.path.basename(os.path.splitext(movie['Path'])[0])
        year_id_pattern = re.compile(r'\(\d{4}\)')
        year_str = year_id_pattern.findall(file_name)[-1]
        file_year = year_str.replace('(', '').replace(')', '')
        file_base_name = file_name.replace(year_str, '').strip()
        # dedected in emby
        movie_name = movie['Name']
        try:
            premier_year = movie['PremiereDate'].split('-')[0]
        except KeyError:
            premier_year = file_year
        # check for error
        error = False
        if file_base_name != movie_name:
            for i, j in enumerate(file_base_name):
                if j != movie_name[i] and j != '-':
                    error = True
                    break
        if file_year != premier_year:
            error = True
        # add to list on error
        if error:
            new_name = f'{movie_name} ({premier_year})'.replace('/', '-')
            old = {'filename': file_name, 'year': file_year}
            new = {'filename': new_name, 'year': premier_year}
            errors_list.append([old, new])
    return errors_list


def rename(config, errors_list):
    """ rename files with correct names """
    print(f'renaming {len(errors_list)} movies.')
    moviepath = config['moviepath']
    skipped = []
    for movie in errors_list:
        old_year = movie[0]['year']
        old_name = movie[0]['filename']
        old_folder = os.path.join(moviepath, old_year, old_name)

        rename_files = os.listdir(old_folder)
        new_year = movie[1]['year']
        new_name = movie[1]['filename']
        # prompt
        print(f'\nrenaming from-to:\n{old_name}\n{new_name}')
        print('[0]: skip')
        print('[1]: rename')
        print('[c]: cancel')
        select = input()
        if select == 0:
            break
        elif select == 'c':
            skipped.append(old_name)
            return
        # continue
        for item in rename_files:
            old_file_name = os.path.join(old_folder, item)
            new_file_name = os.path.join(old_folder, item.replace(old_name, new_name))
            os.rename(old_file_name, new_file_name)
        # movie folder
        os.rename(old_folder, old_folder.replace(old_name, new_name))
        # year folder
        if old_year != new_year:
            old_folder_name = old_folder.replace(f'({old_year})', f'({new_year})')
            new_folder_name = old_folder_name.replace(old_year, new_year)
            os.rename(old_folder_name, new_folder_name)
    return skipped


def get_pending(config):
    """ returns a list of movies with errors """
    movie_list = get_emby_list(config)
    errors_list = compare_list(movie_list)
    return errors_list


def main(config):
    """ main to lunch the id_fix """
    errors_list = get_pending(config)
    if not errors_list:
        print('no errors found')
        sleep(2)
        return
    else:
        skipped = rename(config, errors_list)
    
    if skipped:
        print('skipped following movies:')
        for movie in skipped:
            print(movie)
        input('continue?')
    else:
        print(f'fixed {len(errors_list)} movie names.')
        sleep(2)
