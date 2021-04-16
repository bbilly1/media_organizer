""" download trailers found in emby with youtube-dl """

import os
import re
import requests
import subprocess
import youtube_dl

from time import sleep


def incomplete(config):
    """ search for incomplete downloads and trash them """
    sortpath = config['sortpath']
    file_list = os.listdir(sortpath)
    trashed = False
    for file in file_list:
        if file.endswith('.part') or file.endswith('.ytdl'):
            trashed = True
            file_path = os.path.join(sortpath, file)
            os.path.isfile(file_path)
            subprocess.call(['trash', file_path])
    return trashed


def get_local_trailers(config):
    """ gets a list of existing trailers on filesystem """
    emby_url = config['emby_url']
    emby_api_key = config['emby_api_key']
    url = (emby_url + '/Trailers?api_key=' + emby_api_key + 
        '&Recursive=True&Fields=Path,MediaStreams')
    r = requests.get(url).json()
    local_trailer_list = []
    for movie in r['Items']:
        trailer_name = movie['Name']
        trailing_pattern = re.compile(r'(.*_)([0-9a-zA-Z-_]{11})(-trailer)$')
        youtube_id = trailing_pattern.findall(trailer_name)[0][1]
        movie_name = movie['Path'].split('/')[-2]
        media_streams = movie['MediaSources'][0]['MediaStreams']
        video_stream = list(filter(lambda stream: stream['Type'] == 'Video', media_streams))
        width = video_stream[0]['Width']
        height = video_stream[0]['Height']
        trailer_details = {'movie_name': movie_name, 'youtube_id': youtube_id, 
                        'width': width, 'height': height}
        local_trailer_list.append(trailer_details)
    return local_trailer_list


def get_remote_trailers(config):
    """ get a list of available trailers on emby """
    emby_url = config['emby_url']
    emby_api_key = config['emby_api_key']
    # remote trailer urls
    url = (emby_url + '/Items?api_key=' + emby_api_key + 
        '&Recursive=True&Fields=LocalTrailerCount,RemoteTrailers,Path&' + 
        'IncludeItemTypes=Movie')
    r = requests.get(url).json()
    remote_trailers_list = []
    for movie in r['Items']:
        movie_name = movie['Path'].split('/')[-2]
        movie_path = '/'.join(movie['Path'].split('/')[-3:-1])
        local_trailer_count = movie['LocalTrailerCount']
        remote_trailers = movie['RemoteTrailers']
        trailer_details = {'movie_name': movie_name, 'movie_path': movie_path, 
                        'local_trailer_count': local_trailer_count, 
                        'remote_trailers': remote_trailers}
        remote_trailers_list.append(trailer_details)
    return remote_trailers_list


def compare_download(local_trailer_list, remote_trailers_list, config):
    """ figure out which trailers need downloading """
    # failed before
    log_file = os.path.join(config['log_folder'], 'trailers')
    # check if log file exists
    if not os.path.isfile(log_file):
        # create empty file
        open(log_file, 'a').close()
        failed_ids = []
    else:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        failed_ids = [i.split()[0] for i in lines]
    # ids already downloaded
    local_ids = [i['youtube_id'] for i in local_trailer_list]
    # find pending
    pending = []
    for movie in remote_trailers_list:
        movie_name = movie['movie_name']
        for trailer in movie['remote_trailers']:
            vid_id = trailer['Url'].split('?v=')[1]

            if vid_id not in failed_ids and vid_id not in local_ids:
                pending.append((vid_id, movie_name))
    return pending


def dl_pending(pending, config):
    """ download pending trailers """
    sortpath = config['sortpath']
    ydl_opts = config['ydl_opts']
    # loop thrugh list
    downloaded = []
    for trailer in pending:
        to_down_id = trailer[0]
        movie_name = trailer[1]
        filename = os.path.join(sortpath, movie_name + '_' + to_down_id + '-trailer.mkv')
        ydl_opts['outtmpl'] = filename
        # try up to 5 times
        for i in range(5):
            try:
                print(f'[{i}] {to_down_id} {movie_name}')
                youtube_dl.YoutubeDL(ydl_opts).download(['https://www.youtube.com/watch?v=' + to_down_id])
            except KeyboardInterrupt:
                return False
            except:
                if i == 4:
                    # giving up
                    log_file = os.path.join(config['log_folder'], 'trailers')
                    with open(log_file, 'a') as f:
                        f.write(f'{to_down_id} {movie_name}\n')
                    return False
                else:
                    sleep((i + 1) ** 2)
                    continue
            else:
                downloaded.append(to_down_id)
                break
    return downloaded


def archive(config):
    """ move downloaded trailers to movie archive """
    sortpath = config['sortpath']
    moviepath = config['moviepath']

    new_trailers = os.listdir(sortpath)
    # loop through new trailers
    for trailer in new_trailers:
        # build path
        year_pattern = re.compile(r'(\()([0-9]{4})(\))')
        trailing_pattern = re.compile(r'(.*)(_[0-9a-zA-Z-_]{11}-trailer\.mkv)$')
        movie_name = trailing_pattern.findall(trailer)[0][0]
        year = year_pattern.findall(trailer)[0][1]
        movie_folder = os.path.join(moviepath, year, movie_name)
        # move if all good
        if os.path.isdir(movie_folder):
            old_file = os.path.join(sortpath, trailer)
            new_file = os.path.join(movie_folder, trailer)
            os.rename(old_file, new_file)
    return new_trailers


def get_pending(config):
    """ get a list of pending trailers """
    local_trailer_list = get_local_trailers(config)
    remote_trailers_list = get_remote_trailers(config)
    pending = compare_download(local_trailer_list, remote_trailers_list, config)
    return pending


def main(config):
    """ main function to download pending trailers """
    # check for clean folder
    trashed = incomplete(config)
    # look for trailer
    if not trashed:
        pending = get_pending(config)
    # download if needed
    if pending:
        print(f'downloading {len(pending)} trailers')
        downloaded = dl_pending(pending, config)
    else:
        print('no missing trailers found')
    # move to archive
    if downloaded:
        new_trailers = archive(config)
        print(f'downloaded {len(new_trailers)} new trailers')
