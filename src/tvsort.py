""" handles moving tv downloads """

import logging
import os
import re
import subprocess
from time import sleep

import requests

from src.config import get_config


class Static():
    """ staticmethods collection used from EpisodeIdentify """

    @staticmethod
    def split_file_name(filename):
        """
        takes the file name, returns showname, season, episode and id_style
        based on regex match
        """
        multi_reg = r'[sS][0-9]{1,3}[eE][0-9]{1,3}-?[eE][0-9]{1,3}'
        if re.compile(multi_reg).findall(filename):
            # S01E01-02
            season_id_pattern = re.compile(multi_reg)
            season_id = season_id_pattern.findall(filename)[0]
            get_s_nr = re.compile(r'[0-9]{1,3}')
            season = str(get_s_nr.findall(season_id)[0])
            e_list = get_s_nr.findall(season_id)[1:]
            episode = ' '.join(e_list)
            id_style = 'multi'
        elif re.compile(r'[sS][0-9]{1,3} ?[eE][0-9]{1,3}').findall(filename):
            # S01E01
            season_id_pattern = re.compile(r'[sS]\d{1,3} ?[eE]\d{1,3}')
            season_id = season_id_pattern.findall(filename)[0]
            get_s_nr = re.compile(r'[0-9]{1,3}')
            season = str(get_s_nr.findall(season_id)[0])
            episode = str(get_s_nr.findall(season_id)[1])
            id_style = 'se'
        elif re.compile(r'[0-9]{4}.[0-9]{2}.[0-9]{2}').findall(filename):
            # YYYY.MM.DD
            season_id_pattern = re.compile(r'[0-9]{4}.[0-9]{2}.[0-9]{2}')
            season_id = season_id_pattern.findall(filename)[0]
            season = "NA"
            episode = "NA"
            id_style = 'year'
        elif re.compile(r'0?[0-9][xX][0-9]{1,2}').findall(filename):
            # 01X01
            season_id_pattern = re.compile(r'0?[0-9][xX][0-9]{2}')
            season_id = season_id_pattern.findall(filename)[0]
            get_s_nr = re.compile(r'[0-9]{1,3}')
            season = str(get_s_nr.findall(season_id)[0])
            episode = str(get_s_nr.findall(season_id)[1])
            id_style = 'se'
        elif re.compile(r'[sS][0-9]{1,3}.?[eE][0-9]{1,3}').findall(filename):
            # S01*E01
            season_id_pattern = re.compile(r'[sS]\d{1,3}.?[eE]\d{1,3}')
            season_id = season_id_pattern.findall(filename)[0]
            get_s_nr = re.compile(r'[0-9]{1,3}')
            season = str(get_s_nr.findall(season_id)[0])
            episode = str(get_s_nr.findall(season_id)[1])
            id_style = 'se'
        else:
            # id syle not dealt with
            print('season episode id failed for:')
            print(filename)
            raise ValueError
        return season, episode, season_id, id_style

    @staticmethod
    def showname_encoder(showname):
        """ encodes showname for best possible match """
        # tvmaze doesn't like years in showname
        showname = showname.strip().rstrip('.')
        year_pattern = re.compile(r'\(?[0-9]{4}\)?')
        year = year_pattern.findall(showname)
        if year:
            showname = showname.rstrip(str(year))
        encoded = showname.replace(" ", "%20")
        encoded = encoded.replace(".", "%20").replace("'", "%20")
        return encoded

    @staticmethod
    def tvmaze_request(url):
        """ call the api with back_off on rate limit and user-agent """
        headers = {
            'User-Agent': 'https://github.com/bbilly1/media_organizer'
        }
        # retry up to 5 times
        for i in range(5):
            response = requests.get(url, headers=headers)
            if response.ok:
                # all good
                break
            if response.status_code == 429:
                # rate limited
                print('hit tvmaze rate limiting, slowing down')
            else:
                # general fail
                print('request failed with url:\n' + url)
            # slow down
            back_off = (i + 1) ** 2
            sleep(back_off)
        request = response.json()
        return request


class Episode():
    """ describes single episode """

    def __init__(self, filename, discovered):
        self.filename = filename
        self.discovered = discovered
        self.file_parsed = self.parse_filename()

        showname = self.file_parsed['showname']
        show_id = None
        showname_clean = None
        for i in discovered:
            if showname == i['showname']:
                # found it
                show_id = i['show_id']
                showname_clean = i['showname_clean']
                break
        if not show_id and not showname_clean:
            self.all_results = self.get_show_id()

        self.episode_details = self.get_ep_details(show_id, showname_clean)

    def parse_filename(self):
        """ parse the file name into its parts """
        filename = self.filename
        season, episode, season_id, id_style = Static.split_file_name(filename)
        showname = filename.split(season_id)[0]
        ext = os.path.splitext(filename)[1]
        encoded = Static.showname_encoder(showname)
        # build file_parsed dict
        file_parsed = {}
        file_parsed['showname'] = encoded
        file_parsed['season'] = season
        file_parsed['episode'] = episode
        file_parsed['season_id'] = season_id
        file_parsed['id_style'] = id_style
        file_parsed['ext'] = ext
        # return dict
        return file_parsed

    def get_show_id(self):
        """ return dict of matches """
        showname = self.file_parsed['showname']
        url = 'http://api.tvmaze.com/search/shows?q=' + showname
        request = Static.tvmaze_request(url)
        # loop through results
        all_results = []
        for idx, result in enumerate(request):
            list_id = idx
            show_id = result['show']['id']
            showname_clean = result['show']['name']
            status = result['show']['status']
            desc_raw = result['show']['summary']
            # filter out basic html tags
            try:
                desc = re.sub('<[^<]+?>', '', desc_raw)
            except TypeError:
                desc = desc_raw
            result_dict = {}
            result_dict['list_id'] = list_id
            result_dict['show_id'] = show_id
            result_dict['showname_clean'] = showname_clean
            result_dict['desc'] = desc
            result_dict['status'] = status
            all_results.append(result_dict)
        # return all_results dict
        return all_results

    def pick_show_id(self):
        """ simple menu to pick matching show manually """
        all_results = self.all_results
        filename = self.filename
        # more than one possibility
        if len(all_results) > 1:
            print(f'\nfilename: {filename}')
            # print menu
            for i in all_results:
                list_id = i['list_id']
                showname_clean = i['showname_clean']
                message = f'[{list_id}] {showname_clean}'
                print(message)
            print('[?] show more\n')
            # select
            select = input('select: ')
            # long menu with desc
            if select == '?':
                # print menu
                for i in all_results[:5]:
                    list_id = i['list_id']
                    showname_clean = i['showname_clean']
                    status = i['status']
                    desc = i['desc']
                    message = (f'[{list_id}] {showname_clean},'
                               + f'status: {status}\n{desc}\n')
                    print(message)
                # select
                select = input('select: ')
        else:
            # only one possibility
            select = 0
        # build string based on selected
        index = int(select)
        show_id = all_results[index]['show_id']
        showname_clean = all_results[index]['showname_clean']
        # return tuble
        return show_id, showname_clean

    def get_ep_details(self, show_id=None, showname_clean=None):
        """ build the show details dict"""
        if not show_id and not showname_clean:
            show_id, showname_clean = self.pick_show_id()
        season, episode, episode_name = self.get_episode_name(show_id)
        episode_details = {}
        episode_details['show_id'] = show_id
        episode_details['showname_clean'] = showname_clean
        episode_details['season'] = season
        episode_details['episode'] = episode
        episode_details['episode_name'] = episode_name
        return episode_details

    def multi_parser(self, show_id):
        """ parse multi episode files names for get_episode_name() """
        file_parsed = self.filename
        season = file_parsed['season']
        episode_list = file_parsed['episode'].split()
        # loop through all episodes
        episode_name_list = []
        for episode in episode_list:
            url = (f'http://api.tvmaze.com/shows/{show_id}/episodebynumber?'
                   f'season={season}&number={episode}')
            request = Static.tvmaze_request(url)
            episode_name = request['name']
            episode_name_list.append(episode_name)

        episode = '-E'.join(episode_list)
        episode_name = ', '.join(episode_name_list)
        return season, episode, episode_name

    def get_episode_name(self, show_id):
        """ find episode based on show_id and id_style """
        file_parsed = self.file_parsed
        id_style = file_parsed['id_style']
        # multi episode filename
        if id_style == 'multi':
            # build and return tuple on multi episode
            season, episode, episode_name = self.multi_parser(show_id)
            return season, episode, episode_name
        # season - episode based
        if id_style == 'se':
            season = file_parsed['season']
            episode = file_parsed['episode']
            url = (f'http://api.tvmaze.com/shows/{show_id}/episodebynumber?'
                   f'season={season}&number={episode}')
            request = Static.tvmaze_request(url)
            # returns a dict
            show_response = request
        # date based
        elif id_style == 'year':
            date_raw = file_parsed['season_id']
            year, month, day = date_raw.split('.')
            url = (f'https://api.tvmaze.com/shows/{show_id}/episodesbydate?'
                   f'date={year}-{month}-{day}')
            request = Static.tvmaze_request(url)
            # returns a list
            show_response = request[0]
        # build and return tuple
        season = str(show_response['season']).zfill(2)
        episode = str(show_response['number']).zfill(2)
        episode_name = show_response['name'].replace('/', '-')
        return season, episode, episode_name


class TvHandler():
    """ handles the tv sort classes """

    CONFIG = get_config()

    def __init__(self):
        self.pending = self.get_pending()
        self.discovered = []

    def get_pending(self):
        """ return how many shows are pending """
        tv_downpath = self.CONFIG['media']['tv_downpath']
        pending = len(os.listdir(tv_downpath))
        return pending

    def move_to_sort(self):
        """ move tv files to sortpath """
        tv_downpath = self.CONFIG['media']['tv_downpath']
        ext = self.CONFIG['media']['ext']
        min_file_size = self.CONFIG['media']['min_file_size']
        sortpath = self.CONFIG['media']['sortpath']
        # walk through tv_downpath
        for dirpath, _, filenames in os.walk(tv_downpath):
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

    def episode_identify(self, to_rename):
        """ loops through the pending list """
        identified = []
        for filename in to_rename:
            episode = Episode(filename, self.discovered)
            # add to discovered
            showname = episode.file_parsed['showname']
            showname_clean = episode.episode_details['showname_clean']
            show_id = episode.episode_details['show_id']
            discovered_item = {}
            discovered_item['showname'] = showname
            discovered_item['showname_clean'] = showname_clean
            discovered_item['show_id'] = show_id
            self.discovered.append(discovered_item)
            identified.append(episode)
        return identified

    def episode_rename(self, identified):
        """ make folder and rename files as identified """
        sortpath = self.CONFIG['media']['sortpath']
        renamed = []
        for episode in identified:
            # build vars
            ext = episode.file_parsed['ext']
            showname_clean = episode.episode_details['showname_clean']
            season = episode.episode_details['season']
            season_int = int(season)
            episode_id = episode.episode_details['episode']
            episode_name = episode.episode_details['episode_name']
            # build paths
            old_file = os.path.join(sortpath, episode.filename)
            new_folder = os.path.join(sortpath, showname_clean,
                                      f'Season {season_int}')
            new_file_name = (f'{showname_clean} - S{season}E{episode_id} - '
                             + f'{episode_name}{ext}')
            new_file = os.path.join(new_folder, new_file_name)
            # do it
            os.makedirs(new_folder, exist_ok=True)
            os.rename(old_file, new_file)
            # finish up
            print(episode.filename)
            renamed.append(new_file)
            logging.info('tv:from [%s] to [%s]', episode.filename, new_file)
        return renamed

    def move_to_archive(self):
        """ moves the renamed files to the archive """
        sortpath = self.CONFIG['media']['sortpath']
        tvpath = self.CONFIG['media']['tvpath']
        print()
        for dirpath, _, filenames in os.walk(sortpath):
            for show in sorted(filenames):
                print(show)
        input('\ncontinue?')
        # apply
        for dirpath, _, filenames in os.walk(sortpath):
            for show in filenames:
                # make folders
                folder_name = dirpath.lstrip(sortpath)
                new_folder = os.path.join(tvpath, folder_name)
                os.makedirs(new_folder, exist_ok=True)
                # move file
                old_file = os.path.join(sortpath, dirpath, show)
                new_file = os.path.join(new_folder, show)
                os.rename(old_file, new_file)

    def clean_up(self):
        """ clean up download and sort folder """
        sortpath = self.CONFIG['media']['sortpath']
        tv_downpath = self.CONFIG['media']['tv_downpath']
        to_clean_list = os.listdir(sortpath)
        for to_clean in to_clean_list:
            to_trash = os.path.join(sortpath, to_clean)
            subprocess.call(["trash", to_trash])
        to_clean_list = os.listdir(tv_downpath)
        for to_clean in to_clean_list:
            to_trash = os.path.join(tv_downpath, to_clean)
            subprocess.call(["trash", to_trash])


def main():
    """ main function to sort tv shows """
    handler = TvHandler()
    if not handler.pending:
        print('no tvshows to sort')
        return
    to_rename = handler.move_to_sort()
    if to_rename:
        identified = handler.episode_identify(to_rename)
        renamed = handler.episode_rename(identified)
    if renamed:
        handler.move_to_archive()
        print(f'renamed {len(renamed)} movies')
        handler.clean_up()
