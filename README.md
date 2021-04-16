# media_organizer
*A set of python scripts to rename movies and tv shows.*

This project is used and tested under Linux and is ideal to be used from something like a Raspberry Pi or a Linux based NAS. If you want to help me to get it to work under Windows, please contribute.

## Run
Clone the repo, setup config file (see below) and run `interface.py`.

## moviesort
Detect movie names by querying [themoviedb.org](https://www.themoviedb.org/) API and renaming the file based on a selection of possible matches. Follow the config file instructions bellow to get your API key.

All data is courtesy of [The Movie Database](https://www.themoviedb.org), please contribute to this excellent database.

Movies will get renamed to this nameing style, a more flexible solution is in pending:  
**{movie-name} {Year}/{movie-name} {Year}.{ext}**

## tvsort
Detect tv show filenames by querying the publicly available [tvmaze.com](https://www.tvmaze.com/) API to identify the show name and the episode name based on a selection of possible matches.

Episodes are named in this style, a more flexible solution is in pending:  
**{show-name}/Season {nr}/show-name - S{nr}E{nr} - {episode-name}.{ext}**

## db_export
Export the library to csv files. Calles the Emby API to get a list of movies and episodes and exports this to a convenient set ov CSV files.

## trailers
Downloading trailers from links provided from emby and move them into the movie folder.  
Trailers are named in this style, a more flexible solution is in pending:  
**{movie-name} {Year}_{youtube-id}_trailer.mkv**

## setup
### install
These are the none standard Python libraries in use in this project:
* [requests](https://pypi.org/project/requests/)
    * Install on Arch: `sudo pacman -Qi python-request`
    * Install with pip: `pip install request`
* [trash-cli](https://pypi.org/project/trash-cli/)
    * Install on Arch: `sudo pacman -S trash-cli`
    * Install with pip: `pip install trash-cli`
* [youtube-dl](https://pypi.org/project/youtube_dl/)
    * Install on Arch: `sudo pacman -S youtube-dl`
    * Install with pip: `pip install youtube_d`
* curses
    * Is already installed on most linux based systems.
    * On Windows: `pip install windows-curses`

### config file:
Duplicate the config.sample file to a file named *config* and set the following variables:
* `tv_downpath`: Folder path where the tv episodes get downloaded to.
* `movie_downpath`: Folder path where the movie files get downloaded to.
* `sortpath`: Empty folder the media_organizer can use to as a temporary sort path.
* `moviepath`: Root folder where the organized movie files will go.
* `tvpath`: Root folder where the organized tv episodes will go.
* `ext`: A space separated list of valid media file extensions to easily filter out none media related files.
* `log_path`: Path to a folder to output all renaming done to keep track and check for any errors and safe csv files.
* `movie_db_api`: Register and get your themoviedb.com **API Key (v3 auth)** acces from [here](https://www.themoviedb.org/settings/api).  

*Emby integration:*  
* `emby_url`: url where your emby instance is reachable
* `emby_user_id`: user id of your emby user
* `emby_api_key`: api key for your user on emby  

*Trailer download:*  
Arguments under the [ydl_opts] section will get passed in to youtube-dl. Check out the documentation for details.