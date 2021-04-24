""" sort and rename downloaded movies """

import logging
import os
import re
import requests
import subprocess
from time import sleep


def get_pending(movie_downpath):
    """ 
    return how many movies are pending 
    return 0 when nothing to do
    """
    pending = len(os.listdir(movie_downpath))
    return pending


def move_to_sort(movie_downpath, sortpath, ext):
    """ moves movies to sortpath """
    for dirpath, _, filenames in os.walk(movie_downpath):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            _, extension = os.path.splitext(path)
            extension = extension.lstrip('.').lower()
            f_size = os.stat(path).st_size
            # TODO: set f_size in config.json
            if extension in ext and 'sample' not in filename and f_size > 50000000:
                move_to = os.path.join(sortpath, filename)
                os.rename(path, move_to)
    pending = os.listdir(sortpath)
    return pending


def split_filename(filename):
    """ split the filename into moviename, year, file_ext """
    print(filename)
    file_ext = os.path.splitext(filename)[1]
    year_id_pattern = re.compile(r'\d{4}')
    year_list = year_id_pattern.findall(filename)
    # remove clear false
    for year in year_list:
        if year == '1080':
            # there were no movies back in 1080
            year_list.remove(year)
        file_split = filename.split(year)
        if len(file_split[0]) == 0:
            year_list.remove(year)
    if len(year_list) != 1:
        print('year extraction failed for: ' + filename)
        year = input('whats the year?\n')
    else:
        year = year_list[0]
    moviename = filename.split(year)[0].rstrip('.')
    return moviename, year, file_ext


def get_results(movie_db_api, moviename, year = None):
    """ return results from api call """
    moviename_encoded = moviename.lower().replace("its", "")\
        .replace(" ", "%20").replace(".", "%20").replace("'", "%20")
    # call api with year passed or not
    if year:
        request = requests.get('https://api.themoviedb.org/3/search/movie?api_key=' + 
                        movie_db_api + '&query=' + moviename_encoded + '&year=' + 
                        year + '&language=en-US&include_adult=false').json()
    else:
        request = requests.get('https://api.themoviedb.org/3/search/movie?api_key=' + 
                        movie_db_api + '&query=' + moviename_encoded + 
                        '&language=en-US&include_adult=false').json()
    try:
        results = len(request['results'])
    except KeyError:
        results = 0
    if results == 0:
        # try again without last word of string
        moviename_encoded = '%20'.join(moviename_encoded.split('%20')[0:-1])
        request = requests.get('https://api.themoviedb.org/3/search/movie?api_key=' + 
                        movie_db_api + '&query=' + moviename_encoded + '&year=' + 
                        year + '&language=en-US&include_adult=false').json()
        results = len(request['results'])
    # return
    return results, request


def search_for(movie_db_api, moviename, filename, year = None):
    """ 
    takes the moviename and year from the filename 
    and returns clean name and year
    """
    # get results from API
    results, request = get_results(movie_db_api, moviename, year)
    # clear when only one result
    if results == 1:
        selection = 0
    # select for more than 0 result
    elif results > 0:
        short_list = []
        long_list = []
        counter = 0
        for item in request['results']:
            movie_title = item['title']
            movie_date = item['release_date']
            movie_year = movie_date.split('-')[0]
            movie_desc = item['overview']
            short_list_str = f'[{str(counter)}] {movie_title} - {movie_year}'
            long_list_str = f'{short_list}\n{movie_desc}'
            short_list.append(short_list_str)
            long_list.append(long_list_str)
            counter = counter + 1
        short_list.append('[?] show more')
        # print short menu
        print('\nfilename: ' + filename)
        for line in short_list:
            print(line)
        selection = input('select input: ')
        # print long menu
        if selection == '?':
            for line in long_list:
                print(line)
            selection = input('select input: ')
    # no result, try again
    else:
        return None, None
    # get and return title and year
    movie_title = request['results'][int(selection)]['title']
    movie_year = request['results'][int(selection)]['release_date'].split('-')[0]
    return movie_title, movie_year


def movie_rename(sortpath, movie_db_api):
    """ renames the movie file """
    to_rename = os.listdir(sortpath)
    # os.chdir(sortpath)
    for filename in to_rename:
        # split up
        moviename, year, file_ext = split_filename(filename)
        # try to figure things out
        while True:
            # first try
            movie_title, movie_year = search_for(movie_db_api, moviename, filename, year, )
            if movie_title and movie_year:
                break
            # second try with - 1 year
            movie_title, movie_year = search_for(movie_db_api, moviename, filename, str(int(year) - 1), )
            if movie_title and movie_year:
                break
            # third try with + 1 year
            movie_title, movie_year = search_for(movie_db_api, moviename, filename, str(int(year) + 1), )
            if movie_title and movie_year:
                break
            # last try without year
            movie_title, movie_year = search_for(movie_db_api, moviename, filename)
            if movie_title and movie_year:
                break
            # manual overwrite
            print(filename + '\nNo result found, search again with:')
            moviename = input('movie name: ')
            year = input('year: ')
            movie_title, movie_year = search_for(moviename, year, filename)
            break
        if not movie_title or not movie_year:
            # last check
            return False
        else:
            # clean invalid chars
            movie_title = movie_title.replace('/', '-')
            # do it
            rename_to = movie_title + ' (' + movie_year + ')' + file_ext
            old_file = os.path.join(sortpath, filename)
            new_file = os.path.join(sortpath, rename_to)
            os.rename(old_file, new_file)
            logging.info('movie:from [{}] to [{}]'.format(filename,rename_to))
    return True


def move_to_archive(sortpath, moviepath):
    """ moves renamed movie to archive,
    returns list for further processing """
    new_movies = []
    to_move = os.listdir(sortpath)
    if to_move:
        print()
        for i in to_move:
            print(i)
        _ = input('\ncontinue?')
        to_move = os.listdir(sortpath)
        for movie in to_move:
            movie_name = os.path.splitext(movie)[0]
            year_pattern = re.compile(r'(\()([0-9]{4})(\))')
            year = year_pattern.findall(movie_name)[0][1]
            old_file = os.path.join(sortpath, movie)
            new_folder = os.path.join(moviepath, year, movie_name)
            new_file = os.path.join(new_folder, movie)
            try:
                os.makedirs(new_folder)
            except FileExistsError:
                print(f'{movie_name}\nalready exists in archive')
                double = input('[o]: overwrite, [s]: skip and ignore\n')
                if double == 'o':
                    subprocess.call(["trash", new_folder])
                    os.makedirs(new_folder)
                elif double == 's':
                    continue
            else:
                pass
            finally:
                pass
            os.rename(old_file, new_file)
            new_movies.append(movie_name)
    return new_movies


# clean up
def cleanup(movie_downpath, sortpath, renamed):
    """ cleans up the movie_downpath folder """
    if renamed:
        # renamed without errors
        to_clean_list = os.listdir(movie_downpath)
        for to_clean in to_clean_list:
            to_trash = os.path.join(movie_downpath, to_clean)
            subprocess.call(["trash", to_trash])
        to_clean_list = os.listdir(sortpath)
        for to_clean in to_clean_list:
            to_trash = os.path.join(sortpath, to_clean)
            subprocess.call(["trash", to_trash])
    else:
        # failed to rename
        move_back = os.listdir(sortpath)
        for movie in move_back:
            old_path = os.path.join(sortpath, movie)
            new_path = os.path.join(movie_downpath, movie)
            os.rename(old_path, new_path)


def main(config):
    """ main to sort movies """
    # read config
    movie_downpath = config['media']['movie_downpath']
    sortpath = config['media']['sortpath']
    moviepath = config['media']['moviepath']
    ext = config['media']['ext']
    movie_db_api = config['media']['movie_db_api']
    # check if pending
    pending = get_pending(movie_downpath)
    if not pending:
        print('no movies to sort')
        sleep(2)
        return
    
    # move to sort folder
    pending = move_to_sort(movie_downpath, sortpath, ext)
    if not pending:
        print('no movies to sort')
        sleep(2)
        return
    
    movie_renamed = movie_rename(sortpath, movie_db_api)
    if movie_renamed:
        renamed = move_to_archive(sortpath, moviepath)
        # clean folders
        cleanup(movie_downpath, sortpath, renamed)
