""" download trailers found in emby with youtube-dl """

import os
import re

from time import sleep

import requests
import youtube_dl

from src.config import get_config


class TrailerHandler:
    """ holds the trailers """

    CONFIG = get_config()

    def __init__(self):
        self.pending = self.get_pending()

    def get_local_trailers(self):
        """ gets a list of existing trailers on filesystem """
        emby_url = self.CONFIG['emby']['emby_url']
        emby_api_key = self.CONFIG['emby']['emby_api_key']
        url = (emby_url + '/Trailers?api_key=' + emby_api_key
               + '&Recursive=True&Fields=Path')
        request = requests.get(url).json()
        local_trailer_list = []
        for movie in request['Items']:
            trailer_name = movie['Name']
            trailing_reg = r'(.*_)([0-9a-zA-Z-_]{11})(-trailer)$'
            trailing_pattern = re.compile(trailing_reg)
            youtube_id = trailing_pattern.findall(trailer_name)[0][1]
            movie_name = movie['Path'].split('/')[-2]
            trailer_details = {
                'movie_name': movie_name,
                'youtube_id': youtube_id
            }
            local_trailer_list.append(trailer_details)
        return local_trailer_list

    def get_remote_trailers(self):
        """ get a list of available trailers on emby """
        emby_url = self.CONFIG['emby']['emby_url']
        emby_api_key = self.CONFIG['emby']['emby_api_key']
        # remote trailer urls
        url = (emby_url + '/Items?api_key=' + emby_api_key +
               '&Recursive=True&Fields=RemoteTrailers,Path' +
               '&IncludeItemTypes=Movie')
        request = requests.get(url).json()
        remote_trailers_list = []
        for movie in request['Items']:
            movie_name = movie['Path'].split('/')[-2]
            remote_trailers = movie['RemoteTrailers']
            for remote_trailer in remote_trailers:
                url = remote_trailer['Url']
                youtube_id = url.split('?v=')[1]
                trailer_details = {
                    'movie_name': movie_name,
                    'youtube_id': youtube_id
                }
                remote_trailers_list.append(trailer_details)
        return remote_trailers_list

    def get_ignore_trailers(self):
        """ read log file to get list of trailers to ignore """
        log_folder = self.CONFIG['media']['log_folder']
        log_file = os.path.join(log_folder, 'trailers')
        with open(log_file, 'r') as log_file:
            trailer_lines = log_file.readlines()
        ignore_trailer_list = []
        for trailer_line in trailer_lines:
            youtube_id = trailer_line.split()[0]
            movie_name = trailer_line.lstrip(youtube_id).strip()
            trailer_details = {
                'movie_name': movie_name,
                'youtube_id': youtube_id
            }
            ignore_trailer_list.append(trailer_details)
        return ignore_trailer_list

    def get_pending(self):
        """ compare have and pending """
        remote_trailers_list = self.get_remote_trailers()
        local_trailer_list = self.get_local_trailers()
        ignore_trailer_list = self.get_ignore_trailers()
        # add local and ignore list together
        have_trailers = ([i['youtube_id'] for i in local_trailer_list]
                         + [i['youtube_id'] for i in ignore_trailer_list])
        # add to pending if missing
        pending = []
        for remote_trailer in remote_trailers_list:
            youtube_id = remote_trailer['youtube_id']
            if youtube_id not in have_trailers:
                pending.append(remote_trailer)
        return pending

    def dl_pending(self):
        """ download pending trailers """
        sortpath = self.CONFIG['media']['sortpath']
        log_folder = self.CONFIG['media']['log_folder']
        ydl_opts = self.CONFIG['ydl_opts']
        # loop thrugh list
        trailers_downloaded = []
        for trailer in self.pending:
            youtube_id = trailer['youtube_id']
            movie_name = trailer['movie_name']
            filename = f'{movie_name}_{youtube_id}-trailer.mkv'
            filepath = os.path.join(sortpath, filename)
            ydl_opts['outtmpl'] = filepath
            # try up to 5 times
            for i in range(5):
                try:
                    print(f'[{i}] {youtube_id} {movie_name}')
                    url = 'https://www.youtube.com/watch?v=' + youtube_id
                    youtube_dl.YoutubeDL(ydl_opts).download([url])
                except KeyboardInterrupt:
                    return False
                except Exception:
                    if i == 4:
                        # giving up
                        log_file = os.path.join(log_folder, 'trailers')
                        with open(log_file, 'a') as f:
                            f.write(f'{youtube_id} {movie_name}\n')
                        break
                    sleep((i + 1) ** 2)
                    continue
                else:
                    trailers_downloaded.append(trailer)
                    break
        return trailers_downloaded

    def archive(self):
        """ move downloaded trailers to movie archive """
        sortpath = self.CONFIG['media']['sortpath']
        moviepath = self.CONFIG['media']['moviepath']

        new_trailers = os.listdir(sortpath)
        # loop through new trailers
        for trailer in new_trailers:
            # build path
            year_pattern = re.compile(r'(\()([0-9]{4})(\))')
            trailing_reg = r'(.*)(_[0-9a-zA-Z-_]{11}-trailer.mkv)$'
            trailing_pattern = re.compile(trailing_reg)
            movie_name = trailing_pattern.findall(trailer)[0][0]
            year = year_pattern.findall(trailer)[0][1]
            movie_folder = os.path.join(moviepath, year, movie_name)
            # move if all good
            if os.path.isdir(movie_folder):
                old_file = os.path.join(sortpath, trailer)
                new_file = os.path.join(movie_folder, trailer)
                os.rename(old_file, new_file)
        return new_trailers


def main():
    """ check and download missing trailers """
    handler = TrailerHandler()
    if handler.pending:
        print(f'downloading {len(handler.pending)} trailers')
        sleep(2)
        downloaded = handler.dl_pending()
    else:
        downloaded = False
        print('no missing trailers found')
        sleep(2)
        return
    if downloaded:
        new_trailers = handler.archive()
        print(f'downloaded {len(new_trailers)} new trailers')
        sleep(2)
