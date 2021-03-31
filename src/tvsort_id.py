""" handles id and renaming tv download files """

import logging
import os
import re
import requests


def split_file_name(filename):
    """ 
    takes the file name, returns showname, season, episode and id_style 
    based on regex match
    """
    if re.compile(r'[sS][0-9]{1,3}[eE][0-9]{1,3}-?[eE][0-9]{1,3}').findall(filename):
        # S01E01-02
        season_id_pattern = re.compile(r'[sS][0-9]{1,3}[eE][0-9]{1,3}-?[eE][0-9]{1,3}')
        season_id = season_id_pattern.findall(filename)[0]
        get_s_nr = re.compile(r'[0-9]{1,3}')
        s = str(get_s_nr.findall(season_id)[0])
        e_list = get_s_nr.findall(season_id)[1:]
        e = ' '.join(e_list)
        id_style = 'multi'
    elif re.compile(r'[sS][0-9]{1,3} ?[eE][0-9]{1,3}').findall(filename):
        # S01E01
        season_id_pattern = re.compile(r'[sS]\d{1,3} ?[eE]\d{1,3}')
        season_id = season_id_pattern.findall(filename)[0]
        get_s_nr = re.compile(r'[0-9]{1,3}')
        s = str(get_s_nr.findall(season_id)[0])
        e = str(get_s_nr.findall(season_id)[1])
        id_style = 'se'
    elif re.compile(r'[0-9]{4}.[0-9]{2}.[0-9]{2}').findall(filename):
        # YYYY.MM.DD
        season_id_pattern = re.compile(r'[0-9]{4}.[0-9]{2}.[0-9]{2}')
        season_id = season_id_pattern.findall(filename)[0]
        s = "NA"
        e = "NA"
        id_style = 'year'
    elif re.compile(r'0?[0-9][xX][0-9]{1,2}').findall(filename):
        # 01X01
        season_id_pattern = re.compile(r'0?[0-9][xX][0-9]{2}')
        season_id = season_id_pattern.findall(filename)[0]
        get_s_nr = re.compile(r'[0-9]{1,3}')
        s = str(get_s_nr.findall(season_id)[0])
        e = str(get_s_nr.findall(season_id)[1])
        id_style = 'se'
    elif re.compile(r'[sS][0-9]{1,3}.?[eE][0-9]{1,3}').findall(filename):
        # S01*E01
        season_id_pattern = re.compile(r'[sS]\d{1,3}.?[eE]\d{1,3}')
        season_id = season_id_pattern.findall(filename)[0]
        get_s_nr = re.compile(r'[0-9]{1,3}')
        s = str(get_s_nr.findall(season_id)[0])
        e = str(get_s_nr.findall(season_id)[1])
        id_style = 'se'
    else:
        # id syle not dealt with
        print('season episode id failed for:')
        print(filename)
        raise ValueError
    showname = filename.split(season_id)[0]
    encoded = showname_encoder(showname)
    # build file_details dict
    file_details = {}
    file_details['showname'] = encoded
    file_details['season'] = s
    file_details['episode'] = e
    file_details['season_id'] = season_id
    file_details['id_style'] = id_style
    # return dict
    return file_details


def showname_encoder(showname):
    """ encodes showname for best possible match """
    encoded = showname.rstrip('.')\
            .strip().replace(" ", "%20")\
            .replace(".", "%20").replace("'", "%20")
    return encoded


def get_show_id(file_details):
    """ return dict of matches """
    showname = file_details['showname']
    url = 'http://api.tvmaze.com/search/shows?q=' + showname
    request = requests.get(url).json()
    # loop through results
    all_results = []
    for idx, result in enumerate(request):
        list_id = idx
        show_id = result['show']['id']
        showname_clean = result['show']['name']
        status = result['show']['status']
        desc_raw = result['show']['summary']
        desc = re.sub('<[^<]+?>', '', desc_raw)
        result_dict = {}
        result_dict['list_id'] = list_id
        result_dict['show_id'] = show_id
        result_dict['showname_clean'] = showname_clean
        result_dict['desc'] = desc
        result_dict['status'] = status
        all_results.append(result_dict)
    # return all_results dict
    return all_results


def pick_show_id(all_results):
    """ simple menu to pick matching show manually """
    # more than one possibility
    if len(all_results) > 1:
        # print menu
        for i in all_results:
            list_id = i['list_id']
            showname_clean = i['showname_clean']
            message = f'[{list_id}] {showname_clean}'
            print(message)
        print('\n[?] show more')
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
                message = f'[{list_id}] {showname_clean}, status: {status}\n{desc}\n'
                print(message)
            # select
            select = input('select: ')
    else:
        # only one possibility
        select = 0
    # build string based on selected
    index = int(select)
    show_id = all_results[index]['show_id']
    show_name_clean = all_results[index]['showname_clean']
    # return tuble
    return show_id, show_name_clean



def multi_parser(file_details, show_id):
    """ parse multi episode files names """
    season = file_details['season']
    episode_list = file_details['episode'].split()
    # loop through all episodes
    episode_name_list = []
    for episode in episode_list:
        url = f'http://api.tvmaze.com/shows/{show_id}/episodebynumber?season={season}&number={episode}'
        request = requests.get(url).json()
        episode_name = request['name']
        episode_name_list.append(episode_name)

    episode = '-E'.join(episode_list)
    episode_name = ', '.join(episode_name_list)
    return season, episode, episode_name


def get_episode_name(file_details, show_id):
    """ find episode based on show_id and id_style """
    id_style = file_details['id_style']
    # multi episode filename
    if id_style == 'multi':
        # build and return tuple on multi episode
        season, episode, episode_name = multi_parser(file_details, show_id)
        return season, episode, episode_name
    # season - episode based
    if id_style == 'se':
        season = file_details['season']
        episode = file_details['episode']
        url = f'http://api.tvmaze.com/shows/{show_id}/episodebynumber?season={season}&number={episode}'
        request = requests.get(url).json()
        # returns a dict
        show_response = request
    # date based
    elif id_style == 'year':
        date_raw = file_details['season_id']
        year, month, day = date_raw.split('.')
        url = f'https://api.tvmaze.com/shows/{show_id}/episodesbydate?date={year}-{month}-{day}'
        request = requests.get(url).json()
        # returns a list
        show_response = request[0]
    # build and return tuple
    season = str(show_response['season']).zfill(2)
    episode = str(show_response['number']).zfill(2)
    episode_name = show_response['name']
    return season, episode, episode_name


def episode_rename(config):
    """ loops through all files in sortpath """
    sortpath = config['sortpath']
    # poor man's cache
    cache = {}
    cache['last_show_name'] = None
    cache['last_show_id'] = None
    cache['last_show_name_clean'] = None
    # to rename
    to_rename = sorted(os.listdir(sortpath), key=str.casefold)
    # start the loop
    renamed = []
    for filename in to_rename:
        file_details = split_file_name(filename)
        last_show_name = file_details['showname'].lower()
        # check cach
        if last_show_name == cache['last_show_name']:
            # already in cache, no need to search again
            show_id = cache['last_show_id']
            show_name_clean = cache['last_show_name_clean']
        else:
            # not in cache, search
            all_results = get_show_id(file_details)
            show_id, show_name_clean = pick_show_id(all_results)
            # update cache
            cache['last_show_name'] = last_show_name.lower()
            cache['last_show_id'] = show_id
            cache['last_show_name_clean'] = show_name_clean
        # get episode specific details
        season, episode, episode_name = get_episode_name(file_details, show_id)
        # build new filename
        ext = os.path.splitext(filename)[1]
        s_clean = season.lstrip('0')
        new_folder = os.path.join(sortpath, show_name_clean, 'Season ' + s_clean)
        rename_to = f'{show_name_clean} - S{season}E{episode} - {episode_name}{ext}'
        old_file = os.path.join(sortpath, filename)
        new_file = os.path.join(sortpath, new_folder, rename_to)
        # make folder and move
        os.makedirs(new_folder, exist_ok=True)
        os.rename(old_file, new_file)
        # output
        print(new_file)
        renamed.append(rename_to)
        logging.info('tv:from [{}] to [{}]'.format(filename,rename_to))
    # return new filenames
    return renamed
