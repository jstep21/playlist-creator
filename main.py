import os
import re
from random import random, randrange, shuffle

import requests
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, render_template, url_for, session, redirect, jsonify

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")
USERNAME = os.environ.get("USERNAME")
DEVICE_ID = os.environ.get("DEVICE_ID")


app = Flask(__name__)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope='user-library-read playlist-modify-public playlist-modify-private '
                                                     'streaming '
                                                     'user-read-playback-state user-modify-playback-state',
                                               show_dialog=True,
                                               cache_path='.cache',
                                               username=USERNAME
                                               ))


def get_daylist():
    current_playlists = sp.current_user_playlists()['items']
    current_daylist = {}

    for playlist in current_playlists:
        if 'daylist' in playlist['name']:
            current_daylist = {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'image': playlist['images'][0]['url']
            }
    return current_daylist


@app.route('/', methods=['GET', 'POST'])
def home():
    """Renders home route.
    When the user first enters the page, get their current Spotify daylist and associated mood tags.
    When the user generates a new playlist, take user choices for number of songs and mood tags and create new
    playlist"""
    if request.method == 'GET':
        daylist_dict = get_daylist()

        # UNCOMMENT CODE BELOW TO SEE YOUR AVAILABLE AUDIO DEVICES FOR PLAYBACK
        # ADD THE DEVICE ID TO A "DEVICE_ID" ENVIRONMENT VARIABLE
        # devices = sp.devices()
        # print(devices)

        if not daylist_dict:
            return 'Daylist not found'

        current_daylist = sp.playlist_items(daylist_dict['id'])

        anchor_words = re.findall(r'<a href="([^"]*)">([^<]*)</a>', daylist_dict['description'])
        anchor_playlists = [sp.playlist_items(playlist.split(':')[2]) for playlist, word in anchor_words]
        songs = [song['track'] for song in current_daylist['items']]

        return render_template(template_name_or_list='index.html',
                               daylist_info=daylist_dict,
                               songs=songs,
                               anchor_words=anchor_words,
                               anchor_playlists=anchor_playlists
                               )
    else:
        new_playlist = []
        daylist_dict = get_daylist()

        songs_per_mood = int(request.form.get('num_songs'))
        seed_playlists = request.form.getlist('selected_assets')
        seed_playlists = [tuple(item.split('|')) for item in seed_playlists]

        hrefs = [href for href, word in seed_playlists]
        chosen_moods = [word for href, word in seed_playlists]
        new_playlist_words = []

        for i in range(3):
            rand_index = randrange(len(chosen_moods))
            new_playlist_words.append(chosen_moods[rand_index])
            chosen_moods.remove(chosen_moods[rand_index])

        print(new_playlist_words)
        name_split = daylist_dict['name'].split()
        time_of_day = name_split[len(name_split)-1]
        day_of_week = name_split[len(name_split)-2]
        new_playlist_name = (f'{new_playlist_words[0]} {new_playlist_words[1]} for {new_playlist_words[2]}'
                             f' {time_of_day}s')

        chosen_playlist_ids = [href.split('st:')[1] for href in hrefs]
        chosen_playlist_ids.append(daylist_dict['id'])

        chosen_playlist_items = [sp.playlist_items(playlist_id) for playlist_id in chosen_playlist_ids]
        for playlist in chosen_playlist_items:
            for i in range(songs_per_mood):
                successful = False
                while not successful:
                    new_song_index = randrange(len(playlist['items']))
                    new_song = playlist['items'][new_song_index]
                    if new_song not in new_playlist:
                        new_playlist.append(new_song)
                        successful = True
                    else:
                        successful = False

        # where a new playlist will be created...
        # sp.playlist_add_items()
        return render_template('index.html',
                               daylist_info=daylist_dict,
                               new_playlist=new_playlist,
                               new_playlist_name=new_playlist_name)


@app.route('/play', methods=['POST'])
def play_song():
    """Route to handle music playback when the user clicks on a song"""
    data = request.get_json()
    song_uri = data.get('song_uri')

    try:
        sp.transfer_playback(DEVICE_ID)
        sp.start_playback(uris=[song_uri])
        return jsonify(success=True)
    except Exception as e:
        print(e)
        return jsonify(success=False), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
