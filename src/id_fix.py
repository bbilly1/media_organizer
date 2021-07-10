""" looks for movies wrongly identified in emby """

import os
import re
import subprocess
from time import sleep

import requests

from src.config import get_config
from src.db_export import EmbyLibrary


class MovieNameFix:
    """ check movie names in library and
    rename if premiere date doesn't match with filename """

    CONFIG = get_config()

    def __init__(self):
        self.movie_list = self.get_emby_list()
        self.pending = self.find_errors()

    def get_emby_list(self):
        """ get current emby movie list """
        emby_url = self.CONFIG['emby']['emby_url']
        emby_user_id = self.CONFIG['emby']['emby_user_id']
        emby_api_key = self.CONFIG['emby']['emby_api_key']

        url = (f'{emby_url}/Users/{emby_user_id}/Items?api_key={emby_api_key}'
               '&Recursive=True&IncludeItemTypes=Movie'
               '&Fields=Path,PremiereDate')
        request = requests.get(url).json()
        movie_list = request['Items']
        return movie_list

    def find_errors(self):
        """ find missmatch in movie_list """

        errors = []
        for movie in self.movie_list:
            # parse filename
            file_name = os.path.basename(movie['Path'])
            ext = os.path.splitext(file_name)[1]
            movie_name = os.path.splitext(file_name)[0]
            year_id_pattern = re.compile(r'\((\d{4})\)$')
            file_year = year_id_pattern.findall(movie_name)[-1]
            movie_name_file = movie_name.split(f'({file_year})')[0].strip()
            # premier date
            try:
                premier_year = movie['PremiereDate'].split('-')[0]
            except KeyError:
                premier_year = file_year
            # emby
            emby_name = movie['Name']
            error = False
            if emby_name != movie_name_file:
                diff = self.str_diff(emby_name, movie_name_file)
                if diff:
                    error = True
            if premier_year != file_year:
                error = True
            if error:
                error_dict = {
                    'old_year': file_year,
                    'old_name': file_name,
                    'new_year': premier_year,
                    'new_name': f'{emby_name} ({premier_year}){ext}'
                }
                errors.append(error_dict)
        return errors

    @staticmethod
    def str_diff(str1, str2):
        """ simple diff calculator between two strings
        ignoreing - and / """
        diff = []
        for num, value in enumerate(str1):
            try:
                if value not in (str2[num], '/'):
                    diff.append(value)
            except IndexError:
                diff.append(value)
        for num, value in enumerate(str2):
            try:
                if value not in (str1[num], '-'):
                    diff.append(value)
            except IndexError:
                diff.append(value)
        return list(diff)

    def fix_errors(self):
        """ select what to do """
        skipped = []
        fixed = []
        print(f'found {len(self.pending)} problems')
        for error in self.pending:
            old_name = error['old_name']
            new_name = error['new_name']
            # prompt
            print(f'\nrenaming from-to:\n{old_name}\n{new_name}')
            print('[0]: skip')
            print('[1]: rename')
            print('[c]: cancel')
            select = input()

            if select == '1':
                self.rename_files(error)
                fixed.append(new_name)
            elif select == '0':
                skipped.append(old_name)
                continue
            elif select == 'c':
                print('cancel')
                return
            else:
                print(f'{select} is invalid input')
                return
        # pritty output
        if skipped:
            print('skipped files:')
            for i in skipped:
                print(i)
        if fixed:
            print(f'fixed {len(fixed)} movies')

    def rename_files(self, error):
        """ actually rename the files """
        moviepath = self.CONFIG['media']['moviepath']
        old_year = error['old_year']
        new_year = error['new_year']
        old_movie = os.path.splitext(error['old_name'])[0]
        old_folder = os.path.join(moviepath, old_year, old_movie)
        new_movie = os.path.splitext(error['new_name'])[0]
        # handle folder
        if old_year != new_year:
            old_year_folder = os.path.split(old_folder)[0]
            new_year_folder = old_year_folder.replace(old_year, new_year)
            new_folder = os.path.join(new_year_folder, new_movie)
        else:
            new_folder = old_folder.replace(old_movie, new_movie)
        os.makedirs(new_folder)
        # handle files
        for file_name in os.listdir(old_folder):
            old_file = os.path.join(old_folder, file_name)
            new_file_name = file_name.replace(old_movie, new_movie)
            new_file = os.path.join(new_folder, new_file_name)
            os.rename(old_file, new_file)
        # trash now empty folder
        subprocess.call(['trash', old_folder])


def main():
    """ main for fixing movie filenames """
    # stop if scan in progress
    lib_state = EmbyLibrary()
    if not lib_state.ready:
        return

    handler = MovieNameFix()

    if not handler.pending:
        print('no errors found')
        return
    handler.fix_errors()
    sleep(2)
