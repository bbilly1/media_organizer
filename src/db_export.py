""" export collection from emby to CSV """

import csv
from os import path
import requests


def get_items(config):
    """ get json from emby """
    emby_url = config['emby_url']
    emby_user_id = config['emby_user_id']
    emby_api_key = config['emby_api_key']
    # movies
    url = (f'{emby_url}/Users/{emby_user_id}/Items?api_key={emby_api_key}' +
        '&Recursive=true&IncludeItemTypes=Movie' +
        '&fields=Genres,MediaStreams,Overview,ProviderIds' +
        '&SortBy=DateCreated&SortOrder=Descending')
    r = requests.get(url)
    all_movies = r.json()['Items']
    # episodes
    url = (f'{emby_url}/Users/{emby_user_id}/Items?api_key={emby_api_key}' +
        '&IncludeItemTypes=Episode&Recursive=true&StartIndex=0' +
        '&Fields=DateCreated,MediaStreams,MediaSources'
        '&SortBy=DateCreated&SortOrder=Descending&IsMissing=false')

    r = requests.get(url)
    all_episodes = r.json()['Items']
    return all_movies, all_episodes


def parse_movies(all_movies):
    """ loop through the movies """
    movie_info_csv = []
    movie_tech_csv = []
    movie_seen = []
    for movie in all_movies:
        # general
        movie_name = movie['Name']
        overview = movie['Overview']
        imdb = movie['ProviderIds']['Imdb']
        played = movie['UserData']['Played']
        genres = ', '.join(movie['Genres'])
        # media
        for i in movie['MediaSources']:
            if i['Protocol'] == 'File':
                file_name = path.basename(i['Path'])
                year = path.splitext(file_name)[0][-5:-1]
                duration_min = round(i['RunTimeTicks'] / 600000000)
                filesize_MB = round(i['Size'] / 1024 / 1024)
                for j in i['MediaStreams']:
                    if j['Type'] == 'Video':
                        image_width = j['Width']
                        image_height = j['Height']
                        avg_bitrate_MB = round(j['BitRate'] / 1024 / 1024, 2)
                        codec = j['Codec']
                        # found it
                        break
                # found it
                break
        # info csv
        info_dict = {}
        info_dict['movie_name'] = movie_name
        info_dict['year'] = year
        info_dict['imdb'] = imdb
        info_dict['genres'] = genres
        info_dict['overview'] = overview
        info_dict['duration_min'] = duration_min
        movie_info_csv.append(info_dict)
        # technical csv
        tech_dict = {}
        tech_dict['file_name'] = file_name
        tech_dict['duration_min'] = duration_min
        tech_dict['filesize_MB'] = filesize_MB
        tech_dict['image_width'] = image_width
        tech_dict['image_height'] = image_height
        tech_dict['avg_bitrate_MB'] = avg_bitrate_MB
        tech_dict['codec'] = codec
        movie_tech_csv.append(tech_dict)
        # seen or unseen
        if played == True:
            icon = '[X]'
        elif played == False:
            icon = '[ ]'
        seen_line = f'{icon} {movie_name} ({year})'
        movie_seen.append(seen_line)
    
    return movie_info_csv, movie_tech_csv, movie_seen


def write_movie_files(movie_info_csv, movie_tech_csv, movie_seen, config):
    """ writes the csv files to disk """
    log_folder = config['log_folder']

    # movie info
    movie_info_sorted = sorted(movie_info_csv, key=lambda k: k['movie_name'])
    file_path = path.join(log_folder, 'movie-info.csv')
    # open and write
    with open(file_path, 'w') as f:
        # take fieldnames from first line
        fieldnames = movie_info_sorted[0].keys()
        csv_writer = csv.DictWriter(f, fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(movie_info_sorted)

    # movie tech
    movie_tech_csv_sorted = sorted(movie_tech_csv, key=lambda k: k['file_name'])
    file_path = path.join(log_folder, 'movie-tech.csv')
    # open and write
    with open(file_path, 'w') as f:
        # take fieldnames from first line
        fieldnames = movie_tech_csv_sorted[0].keys()
        csv_writer = csv.DictWriter(f, fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(movie_tech_csv_sorted)
    
    # movie by new
    file_path = path.join(log_folder, 'movienew')
    with open(file_path, 'w') as f:
        f.writelines(movie_seen)


def main(config):
    """ write collection to csv """
    # get data
    all_movies, _ = get_items(config)
    # write movies
    movie_info_csv, movie_tech_csv, movie_seen = parse_movies(all_movies)
    write_movie_files(movie_info_csv, movie_tech_csv, movie_seen, config)
