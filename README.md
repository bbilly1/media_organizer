![banner.jpg](assets/media-organizer-banner.png?raw=true "Media Organizer Banner")  

# media_organizer
*A set of python scripts to rename movies and tv shows.*

![screenshot.jpg](assets/media-organizer-screenshot.png?raw=true "Media Organizer Screenshot") 

This project is used and tested under Linux and is ideal to be used from something like a Raspberry Pi or a Linux based NAS. If you want to help me to get it to work under Windows, please contribute.

## Run
Clone the repo, setup config file (see below) and run `interface.py`. Use your arrow keys to navigate up and down the menu.  
* **q** quit the interface
* **r** refresh the pending items by rescanning the file system.

## Movies
Detect movie names by querying [themoviedb.org](https://www.themoviedb.org/) API and renaming the file based on a selection of possible matches. Follow the config file instructions below to get your API key.

All data is courtesy of [The Movie Database](https://www.themoviedb.org), please contribute to this excellent database.

Movies will get renamed to this naming style:  
**{movie-name} ({Year})/{movie-name} ({Year}).{ext}**

## TV shows
Detect tv show filenames by querying the publicly available [tvmaze.com](https://www.tvmaze.com/) API to identify the show name and the episode name based on a selection of possible matches. Please contribute to this excellent database. 

Episodes are named with this template:  
**{show-name}/Season {nr}/show-name - S{nr}E{nr} - {episode-name}.{ext}**

## Trailer download
Download trailers from links provided from emby and move them into the movie folder.  
Trailers are named with this template:  
**{movie-name} ({Year})_{youtube-id}_trailer.mkv**

## Fix Movie Names
Sometimes Emby gets it wrong. Sometimes this script can get it wrong too. The *Fix Movie Names* function goes through the movie library looking for filenames that don't match with the movie name as identified in emby.

## CSV export
Export the library to csv files. Calles the Emby API to get a list of movies and episodes and exports this to a convenient set of CSV files.

## setup
Needs Python >= 3.6 to run.

### install requirements
These are the non standard Python libraries in use in this project:
* [requests](https://pypi.org/project/requests/)
    * Install on Arch: `sudo pacman -S python-requests`
    * Install with pip: `pip install requests`
* [trash-cli](https://pypi.org/project/trash-cli/)
    * Install on Arch: `sudo pacman -S trash-cli`
    * Install with pip: `pip install trash-cli`
* [yt-dlp](https://pypi.org/project/yt-dlp/)
    * Install on Arch: `sudo pacman -S yt-dlp`
    * Install with pip: `pip install yt-dlp`
* curses
    * Is already installed on most linux based systems.
    * On Windows: `pip install windows-curses`

Or use `pip` to install all the requirements:  
`pip install -r requirements.txt`

### config json file:
Duplicate the config.sample.json file to a file named *config.json* and set the following variables:
#### media
* `tv_downpath`: Folder path where the tv episodes get downloaded to.
* `movie_downpath`: Folder path where the movie files get downloaded to.
* `sortpath`: Empty folder that can be used by *media_organizer* as a temporary sort path.
* `moviepath`: Root folder where the organized movie files will go.
* `tvpath`: Root folder where the organized tv episodes will go.
* `ext`: A list of valid media file extensions to easily filter out non-media related files.
* `log_path`: Path to a folder to output all renaming done to keep track, check for any errors and safe csv files.
* `movie_db_api`: Register and get your themoviedb.com **API Key (v3 auth)** acces from [here](https://www.themoviedb.org/settings/api).
* `min_file_size`: Minimal file size to be considered a relevant media file in bytes.  

#### Emby integration
*optional:* remove the 'emby' key from config.json to disable the emby integration. 
* `emby_url`: url where your emby instance is reachable
* `emby_user_id`: user id of your emby user
* `emby_api_key`: api key for your user on emby  

#### ydl_opts *Trailer download:*  
*optional:* remove the 'ydl_opts' key from config.json to disable the trailer download functionality.  
Arguments under the [ydl_opts] section will get passed in to yt-dlp for *trailers*. Check out the documentation for details.

## Known limitations:
Most likely *media_organizer* will fail if there are any files like Outtakes, Extras, Featurettes, etc in the folder. For these cases, move/delete them first before running *media_organizer*.  