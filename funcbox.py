import json
import os
import shutil
import re
import urllib.request
import argparse
from urllib.parse import urlparse
from apiclient.discovery import build
from pytube import YouTube
# to download to a certian directory:
# YouTube('video_url').streams.first().download('save_path')



with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

api_key, max_res = [config[i] for i in ('api_key', 'max_res')]

youtube = build('youtube', 'v3', developerKey=api_key)

# Function called when -a or --add_channel is called in command line.
# -a/--add_channel must be followed by channel link of the form
# .../channel/id or .../user/username
def add_channel(channel_url):
    url_breakdown = urlparse(channel_url)
    channel_key = url_breakdown.path
    if re.match('/channel/\w+', channel_key):
        new_channel = youtube.channels().list(id=channel_key[9:],
                                  part='snippet').execute()
    elif re.match('/user/\w+', channel_key):
        new_channel = youtube.channels().list(forUsername=channel_key[6:],
                                  part='snippet').execute()
    channel_file = open('contents.json', 'r', encoding='utf-8')
    channels = json.load(channel_file)
    channel_file.close()
    for channel in channels:
        if channel['items'][0]['id'] == new_channel['items'][0]['id']:
            raise ValueError('This channel is already saved to your BreadBox')
    channels.append(new_channel)
    with open('contents.json', 'w', encoding='utf-8') as outfile:
        json.dump(channels, outfile, ensure_ascii=False, indent=2)
    print('New channel \"' + new_channel['items'][0]['snippet']['title']
            + '\" has been added to your Breadbox.')
    sync_channel(new_channel)


# Function called when -r or --remove_channel is called in command line.
# Lists all channels in BreadBox using open_breadbox(), then prompts user for
# a number to remove. Removes that channel from content.json.
def remove_channel():
    open_breadbox()
    with open('contents.json', 'r', encoding='utf-8') as contents_file:
        channels = json.load(contents_file)
    if len(channels) != 0:
        removed = input("\nChannel to remove (number): ")
        removed = int(removed)
        try:
            channel = channels[removed - 1]
            channel_file_path = os.path.curdir + '\\videos\\' \
                                    + channel['items'][0]['snippet']['title']
            removed_channel = channels.pop(removed - 1)
            with open('contents.json', 'w', encoding='utf-8') as contents_file:
                json.dump(channels, contents_file, ensure_ascii=False, indent=2)
            shutil.rmtree(channel_file_path)
            print("Channel \"" +
                    removed_channel['items'][0]['snippet']['title']
                    + "\" has been removed from your BreadBox.")
        except IndexError:
            print("Invalid Number. Please select a listed number.\n")
            remove_channel()
    else:
        print('\nYour BreadBox is already empty.\n')


# Displays all channels in contents.json in numbered order.
def open_breadbox():
    with open('contents.json', 'r', encoding='utf-8') as contents_file:
        channels = json.load(contents_file)
    n = 1
    for channel in channels:
        print('\n' + str(n) + '. ' + channel['items'][0]['snippet']['title'])
        n += 1
    if n == 1:
        print('Your BreadBox is empty.\n')

# Takes channel dictionary from contents.json as input, updates existing
# backup for most recent 50 videos.
def sync_channel(channel):
    # Clear discrepencies.txt
    with open('discrepencies.txt', 'w') as outputs:
        outputs.write('')

    channel_file_path = os.path.curdir + '\\videos\\' + channel['items'][0]['snippet']['title']
    if os.path.exists(channel_file_path) == False:
        os.mkdir(channel_file_path)
    print('Fetching most recent 50 videos from channel \"'
            + channel['items'][0]['snippet']['title'] + '\"...')
    videos = get_channel_videos(channel['items'][0]['id'])

    # Add 'path' key to videos dict to be saved to metadata.json in
    # channel folder
    for video in videos:
        title = video['snippet']['title'].lower()
        title = re.sub('[^\w\d\s]', '', title)
        title = re.sub('\s', '-', title)
        video['path'] = title

    print('Fetched.')

    # Checks if videos are saved to the BreadBox
    print('\nChecking for missing local backups...')
    num_of_discrepencies = 0
    try:
        metadata_file = open(channel_file_path + '\\metadata.json',
                    'r', encoding='utf-8')
        metadata = json.load(metadata_file)
    except:
        metadata = []
        print('No metadata saved. Creating new metadata...')

    for video in videos:
        video_in_box = False # Is the video saved? i.e. is the metadata here?
        for metadatum in metadata:
            if metadatum['id'] == video['id']:
                video_in_box = True

        if video_in_box == False:
            # If we find that the video is not in the BreadBox, download it,
            # append its metadatum to the metadata dictionary, then dump the
            # updated metadata dictoinary to metadata.json
            num_of_discrepencies += 1
            print("Video with ID " + str(video['id'])
                    + " is not saved to the BreadBox.")
            print("Downloading...")
            download_at_max_res(video, channel_file_path)
            metadata.append(video)
            with open(channel_file_path + '\\metadata.json', 'w',
                                                encoding='utf-8') as outfile:
                json.dump(metadata, outfile, ensure_ascii=False, indent=2)
            print("Download complete.\n")

    if num_of_discrepencies == 0:
        print('No discrpencies found. Channel \"'
                + channel['items'][0]['snippet']['title'] + '\" is up to date!')

    # Check if metadata from channel is missing anythong from locally backed-up
    # metadata.json
    print('\nChecking for videos missing on the channel...')
    vids_not_online = []
    for metadatum in metadata:
        video_on_channel = False
        for video in videos:
            if metadatum['id'] == video['id']:
                video_on_channel = True

        if video_on_channel == False:
            vids_not_online.append(metadatum)

    if len(vids_not_online) == 0:
        print("The channel \"" + channel['items'][0]['snippet']['title']
                + "\" is not missing any of your most recent 50 backups!")
    else:
        message = "The channel \"" + channel['items'][0]['snippet']['title']
        message += "\" is missing " + str(len(vids_not_online)) + " video(s):\n"
        n = 0
        for video in vids_not_online:
            n += 1
            message += str(n) + ". \"" + video['snippet']['title'] + "\"\n"
        with open('discrepencies.txt', 'a') as outfile:
            outfile.write(message + '\n\n')
        print(message)

def change_max_res():
    possible_res = (2160, 1440, 1080, 720, 480, 360, 240)
    print('Your current resolution is ' + str(max_res) + 'p.\n')
    n = 0
    for res in possible_res:
        n += 1
        print(str(n) + '. ' + str(possible_res[n-1]))
    new_res_index = int(input("\nPlease select your resolution: ")) - 1
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
        config['max_res'] = possible_res[new_res_index]
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
    print('Your maximum resolution has been set to '
            + str(possible_res[new_res_index]) + 'p.')




# Takes in the string of channel_id and returns array of upload dictionary.
# Only called in functions above ^
def get_channel_videos(channel_id):
    # get Uploads playlist id
    res = youtube.channels().list(id=channel_id,
                                  part='contentDetails').execute()
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    videos = []
    next_page_token = None

    while True:
        res = youtube.playlistItems().list(playlistId=playlist_id,
                                           part='snippet,contentDetails',
                                           maxResults=50,
                                           pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')

        if next_page_token is None:
            break

    return videos


def download_at_max_res(video, channel_file_path):
    yt = YouTube('https://www.youtube.com/watch?v='
                    + video['contentDetails']['videoId'])
    res_arr =  [stream.resolution for stream in yt.streams.filter(progressive=True).all()]
    int_res_arr = list(map(lambda res : int(res[:-1]), res_arr))
    download_res = min(int_res_arr)
    for res in int_res_arr:
        if res > download_res and res <= max_res:
            download_res = res
    download_res = str(download_res) + 'p'

    yt.streams.filter(res=download_res).first().download(channel_file_path,
                                                    filename=video['path'])
