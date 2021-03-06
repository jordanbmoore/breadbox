from funcbox import *
import argparse
import os
import json


#If required files do not exist, create them empty.
if os.path.exists(os.path.curdir + "\\videos") == False:
    os.mkdir('videos')

if os.path.exists(os.path.curdir + "\\contents.json") == False:
    with open('contents.json', 'w') as outfile:
        json.dump([], outfile, ensure_ascii=False, indent=2)


if os.path.exists(os.path.curdir + "\\discrepencies.txt") == False:
    open('discrepencies.txt', 'w')

# Configure ArgumentParser
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()

group.add_argument('-a', '--add_channel', default='',
                    help='adds a channel to your breadbox from channel url')
group.add_argument('-r', '--remove_channel', action='store_true',
                    help='removes a channel from your breadbox')
group.add_argument('-o', '--open', action='store_true',
                    help='displays the channels in your breadbox')
group.add_argument('-s', '--sync', action='store_true',
                    help='syncs your backups')
group.add_argument('-q', '--quality', action='store_true',
                    help='change the maximum resolution of your downloads - '
                    + 'this can also be done in config.json by '
                    + 'changing max_res to your desired maximum resolution')


# Parse arguments from command line
args = parser.parse_args()
if args.add_channel != '':
    add_channel(args.add_channel)
elif args.remove_channel:
    remove_channel()
elif args.open:
    open_breadbox()
elif args.sync:
    with open('contents.json', 'r', encoding='utf-8') as contents:
        channels = json.load(contents)
        for channel in channels:
            print('Syncing ' + channel['items'][0]['snippet']['title'] + '...')
            sync_channel(channel)
elif args.quality:
    change_max_res()
