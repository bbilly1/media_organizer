""" sort and rename downloaded movies """

import logging
import os
import re
import subprocess

import requests

from src.config import get_config


class MovieHandler():
    """ handler for moving files around """

    CONFIG = get_config()

    def __init__(self):
        """ check for pending movie files """
        self.pending = self.get_pending()

    def get_pending(self):
        """
        return how many movies are pending
        return 0 when nothing to do
        """
        movie_downpath = self.CONFIG['media']['movie_downpath']
        pending = len(os.listdir(movie_downpath))
        return pending

    def move_to_sort(self):
        """ moving files from movie_downpath to sortpath """
        # read out config
        sortpath = self.CONFIG['media']['sortpath']
        movie_downpath = self.CONFIG['media']['movie_downpath']
        min_file_size = self.CONFIG['media']['min_file_size']
        ext = self.CONFIG['media']['ext']
        for dirpath, _, filenames in os.walk(movie_downpath):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                _, extension = os.path.splitext(path)
                extension = extension.lstrip('.').lower()
                f_size = os.stat(path).st_size
                if (extension in ext and
                        'sample' not in filename and
                        f_size > min_file_size):
                    move_to = os.path.join(sortpath, filename)
                    os.rename(path, move_to)
        pending = os.listdir(sortpath)
        return pending

    def rename_files(self, identified):
        """ apply the identified filenames and rename """
        sortpath = self.CONFIG['media']['sortpath']
        renamed = []
        for movie in identified:
            new_filename = movie.movie_details['new_filename']
            old_file = os.path.join(sortpath, movie.filename)
            new_file = os.path.join(sortpath, new_filename)
            os.rename(old_file, new_file)
            logging.info(
                'movie:from [%s] to [%s]', movie.filename, new_filename
            )
            renamed.append(movie.filename)
        return renamed

    def move_to_archive(self, identified):
        """ move renamed filed to archive """
        sortpath = self.CONFIG['media']['sortpath']
        moviepath = self.CONFIG['media']['moviepath']
        # confirm
        print('\nrenamed:')
        for movie in identified:
            new_filename = movie.movie_details['new_filename']
            print(f'from: {movie.filename} \nto: {new_filename}\n')
        to_continue = input('\ncontinue? Y/n')
        if to_continue == 'n':
            print('cancle...')
            return False
        moved = []
        for movie in identified:
            new_filename = movie.movie_details['new_filename']
            year_dedected = movie.movie_details['year_dedected']
            new_moviename = movie.movie_details['new_moviename']
            new_filename = movie.movie_details['new_filename']
            old_file = os.path.join(sortpath, new_filename)
            new_folder = os.path.join(
                moviepath, str(year_dedected), new_moviename
            )
            new_file = os.path.join(new_folder, new_filename)
            try:
                os.makedirs(new_folder)
            except FileExistsError:
                print(f'{new_filename}\nalready exists in archive')
                double = input('[o]: overwrite, [s]: skip and ignore\n')
                if double == 'o':
                    subprocess.call(["trash", new_folder])
                    os.makedirs(new_folder)
                elif double == 's':
                    continue
            os.rename(old_file, new_file)
            moved.append(new_filename)
        return len(moved)

    def cleanup(self, moved):
        """ clean up movie_downpath and sortpath folder """
        sortpath = self.CONFIG['media']['sortpath']
        movie_downpath = self.CONFIG['media']['movie_downpath']
        if moved:
            # moved without errors
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
            for movie_pending in move_back:
                old_path = os.path.join(sortpath, movie_pending)
                new_path = os.path.join(movie_downpath, movie_pending)
                os.rename(old_path, new_path)


class MovieIdentify():
    """ describes and identifies a single movie """

    CONFIG = get_config()

    def __init__(self, filename):
        """ parse filename """
        self.filename = filename
        self.file_parsed = self.split_filename()
        self.movie_details = self.get_new_filename()

    def split_filename(self):
        """ build raw values from filename """
        file_ext = os.path.splitext(self.filename)[1]
        year_id_pattern = re.compile(r'\d{4}')
        year_list = year_id_pattern.findall(self.filename)
        # remove clear false
        for year in year_list:
            if year in ('1080', '2160'):
                # resolution not year
                year_list.remove(year)
            file_split = self.filename.split(year)
            if len(file_split[0]) == 0:
                year_list.remove(year)
        if len(year_list) != 1:
            print('year extraction failed for:\n' + self.filename)
            year = input('whats the year?\n')
        else:
            year = year_list[0]
        moviename = self.filename.split(year)[0].rstrip('.')
        moviename_encoded = self.encode_moviename(moviename)
        # build file_parsed dict
        file_parsed = {
            'moviename': moviename,
            'moviename_encoded': moviename_encoded,
            'year': int(year),
            'file_ext': file_ext
        }
        return file_parsed

    @ staticmethod
    def encode_moviename(moviename):
        """ url encode and clean the moviename """
        encoded = moviename.lower().replace(' ', '%20')
        encoded = encoded.replace('.', '%20').replace("'", '%20')
        return encoded

    def get_results(self):
        """ get all possible matches """
        movie_db_api = self.CONFIG['media']['movie_db_api']
        year_file = self.file_parsed['year']
        moviename_encoded = self.file_parsed['moviename_encoded']
        # try +/- one year
        year_list = [year_file, year_file + 1, year_file - 1]
        for year in year_list:
            url = (
                'https://api.themoviedb.org/3/search/movie?'
                + f'api_key={movie_db_api}&query={moviename_encoded}'
                + f'&year={year}&language=en-US&include_adult=false'
                )
            request = requests.get(url).json()
            results = request['results']
            # stop if found
            if results:
                break
        return results

    def pick_result(self, results):
        """ select best possible match from list of results """
        if len(results) == 1:
            selection = 0
        elif len(results) > 1:
            short_list = []
            long_list = []
            counter = 0
            for item in results:
                nr = str(counter)
                movie_title = item['title']
                movie_date = item['release_date']
                movie_year = movie_date.split('-')[0]
                movie_desc = item['overview']
                short_list_str = f'[{nr}] {movie_title} - {movie_year}'
                long_list_str = f'{short_list_str}\n{movie_desc}'
                short_list.append(short_list_str)
                long_list.append(long_list_str)
                counter = counter + 1
            short_list.append('[?] show more')
            # print short menu
            print('\nfilename: ' + self.filename)
            for line in short_list:
                print(line)
            selection = input('select input: ')
            # print long menu
            if selection == '?':
                for line in long_list:
                    print(line)
                selection = input('select input: ')
        return int(selection)

    def get_new_filename(self):
        """ get the new filename """
        file_ext = self.file_parsed['file_ext']
        results = self.get_results()
        selection = self.pick_result(results)
        result = results[selection]
        # build new_filename
        year_dedected = result['release_date'].split('-')[0]
        name_dedected = result['title']
        new_moviename = f'{name_dedected} ({year_dedected})'
        new_filename = f'{new_moviename}{file_ext}'
        movie_details = {
            'new_moviename': new_moviename,
            'new_filename': new_filename,
            'year_dedected': year_dedected
        }
        return movie_details


def main():
    """ main to lunch moviesort """
    handler = MovieHandler()
    # check if pending
    if not handler.pending:
        print('no movies to sort')
        return
    to_rename = handler.move_to_sort()
    # identify
    identified = []
    for i in to_rename:
        movie = MovieIdentify(i)
        identified.append(movie)
    # rename and move
    renamed = handler.rename_files(identified)
    if renamed:
        moved = handler.move_to_archive(identified)
        print(f'renamed {moved} movies')
        handler.cleanup(moved)
