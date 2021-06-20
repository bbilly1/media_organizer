""" export collection from emby to CSV """

import csv
from time import sleep
from os import path

import requests

from src.config import get_config


class DatabaseExport():
    """ saves database to CSV """

    CONFIG = get_config()

    def __init__(self):
        self.all_movies, self.all_episodes = self.get_items()

    def get_items(self):
        """ get json from emby """
        emby_url = self.CONFIG['emby']['emby_url']
        emby_user_id = self.CONFIG['emby']['emby_user_id']
        emby_api_key = self.CONFIG['emby']['emby_api_key']
        # movies
        url = (f'{emby_url}/Users/{emby_user_id}/Items?api_key={emby_api_key}'
               '&Recursive=true&IncludeItemTypes=Movie'
               '&fields=Genres,MediaStreams,Overview,'
               'ProviderIds,Path,RunTimeTicks'
               '&SortBy=DateCreated&SortOrder=Descending')
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            sleep(5)
            response = requests.get(url)

        all_movies = response.json()['Items']
        # episodes
        url = (f'{emby_url}/Users/{emby_user_id}/Items?api_key={emby_api_key}'
               '&IncludeItemTypes=Episode&Recursive=true&StartIndex=0'
               '&Fields=DateCreated,Genres,MediaStreams,'
               'MediaSources,Overview,ProviderIds,Path,RunTimeTicks'
               '&SortBy=DateCreated&SortOrder=Descending&IsMissing=false')
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            sleep(5)
            response = requests.get(url)

        all_episodes = response.json()['Items']
        return all_movies, all_episodes

    def parse_movies(self):
        """ handle the movies """
        all_movies = self.all_movies
        # seen
        movie_seen = ListParser.build_seen(all_movies)
        self.write_seen(movie_seen, 'movienew')
        # tech
        movie_tech = ListParser.build_tech(all_movies)
        self.write_csv(movie_tech, 'movie-tech.csv')
        # info
        movie_info = ListParser.build_movie_info(all_movies)
        self.write_csv(movie_info, 'movie-info.csv')

    def parse_episodes(self):
        """ handle the episodes """
        all_episodes = self.all_episodes
        # seen
        episode_seen = ListParser.build_seen(all_episodes)
        self.write_seen(episode_seen, 'episodenew')
        # tech
        episode_tech = ListParser.build_tech(all_episodes)
        self.write_csv(episode_tech, 'episode-tech.csv')
        # info
        episode_info = ListParser.build_episode_info(all_episodes)
        self.write_csv(episode_info, 'episode-info.csv')

    def write_csv(self, to_write, filename):
        """ write list of dicts to CSV """

        log_folder = self.CONFIG['media']['log_folder']
        file_path = path.join(log_folder, filename)

        # open and write
        with open(file_path, 'w') as f:
            # take fieldnames from first line
            fieldnames = to_write[0].keys()
            csv_writer = csv.DictWriter(f, fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(to_write)

    def write_seen(self, to_write, filename):
        """ write list of seen """
        log_folder = self.CONFIG['media']['log_folder']
        file_path = path.join(log_folder, filename)
        # movie by new
        with open(file_path, 'w') as f:
            for line in to_write:
                f.write(line + '\n')


class ListParser():
    """ static parse the lists from DatabaseExport """

    @staticmethod
    def build_seen(filelist):
        """ build the seen list """

        file_item_seen = []

        for file_item in filelist:
            played = file_item['UserData']['Played']
            file_name = path.basename(file_item['Path'])
            file_item_name = path.splitext(file_name)[0]
            # seen or unseen
            if played:
                icon = '[X]'
            else:
                icon = '[ ]'
            seen_line = f'{icon} {file_item_name}'
            file_item_seen.append(seen_line)

        return file_item_seen

    @staticmethod
    def build_tech(filelist):
        """ build tech csv """

        file_item_tech = []

        for file_item in filelist:
            # loop through media sources
            for i in file_item['MediaSources']:
                if i['Protocol'] == 'File':
                    filesize = round(i['Size'] / 1024 / 1024)
                    for j in i['MediaStreams']:
                        if j['Type'] == 'Video':
                            image_width = j['Width']
                            image_height = j['Height']
                            avg_bitrate = round(j['BitRate'] / 1024 / 1024, 2)
                            codec = j['Codec']
                            # found it
                            break
                    # found it
                    break
            # technical csv
            tech_dict = {
                'file_name': path.basename(file_item['Path']),
                'duration_min': round(file_item['RunTimeTicks'] / 600000000),
                'filesize_MB': filesize,
                'image_width': image_width,
                'image_height': image_height,
                'avg_bitrate_MB': avg_bitrate,
                'codec': codec
            }
            file_item_tech.append(tech_dict)

        # sort and return
        file_item_tech_sorted = sorted(
            file_item_tech, key=lambda k: k['file_name']
        )
        return file_item_tech_sorted

    @staticmethod
    def build_movie_info(all_movies):
        """ build movie info csv """

        movie_info = []

        for movie in all_movies:

            info_dict = {
                'movie_name': movie['Name'],
                'year': movie['Path'].split('/')[3],
                'imdb': movie['ProviderIds']['Imdb'],
                'genres': ', '.join(movie['Genres']),
                'overview': movie['Overview'],
                'duration_min': round(movie['RunTimeTicks'] / 600000000)
            }
            movie_info.append(info_dict)

        # sort and return
        movie_info_sorted = sorted(movie_info, key=lambda k: k['movie_name'])
        return movie_info_sorted

    @staticmethod
    def build_episode_info(all_episodes):
        """ build episode info csv """

        episode_info = []

        for episode in all_episodes:
            try:
                episode_id = episode['IndexNumber']
            except KeyError:
                # not a real episode
                continue
            try:
                overview = episode['Overview'].replace('\n\n', ' ')
                overview = overview.replace('\n', ' ')
            except KeyError:
                overview = 'NA'
            try:
                imdb = episode['ProviderIds']['Imdb']
            except KeyError:
                imdb = 'NA'

            # info csv
            info_dict = {
                'episode_id': episode_id,
                'overview': overview,
                'imdb': imdb,
                'episode_name': episode['Name'],
                'file_name': path.basename(episode['Path']),
                'genres': ', '.join(episode['Genres']),
                'series_name': episode['SeriesName'],
                'season_name': episode['SeasonName'],
                'duration_min': round(episode['RunTimeTicks'] / 600000000)
            }
            episode_info.append(info_dict)

        # sort and return
        episode_info_sorted = sorted(
            episode_info, key=lambda k: k['file_name']
        )
        return episode_info_sorted


def main():
    """ main to regenerate csv files """
    print('recreating db files')
    export = DatabaseExport()
    export.parse_movies()
    export.parse_episodes()
