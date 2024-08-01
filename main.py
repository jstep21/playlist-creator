import os
import re
from random import random, randrange, shuffle
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, render_template, url_for, session, redirect, jsonify

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")
USERNAME = os.environ.get("USERNAME")
DEVICE_ID = os.environ.get("DEVICE_ID")
DAYLIST = 'daylist'

app = Flask(__name__)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope='user-library-read playlist-modify-public playlist-modify-private '
                                                     'streaming playlist-read-private '
                                                     'user-read-playback-state user-modify-playback-state',
                                               show_dialog=True,
                                               cache_path='.cache',
                                               username=USERNAME
                                               ))


def get_playlist(playlist_name):
    current_playlists = sp.current_user_playlists()['items']
    playlist_dict = {}

    for playlist in current_playlists:
        print(playlist['name'])
        if playlist_name in playlist['name'] and playlist_name == 'daylist':
            playlist_dict = {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'image': playlist['images'][0]['url']
            }
        elif playlist_name in playlist['name']:
            playlist_dict = {
                'id': playlist['id'],
                'name': playlist['name']
            }
        else:
            return 'playlist not found'

    return playlist_dict


def generate_playlist_name(chosen_moods, daylist_dict):
    """Create a name for the new playlist from the chosen moods"""
    new_playlist_words = []
    for i in range(3):
        rand_index = randrange(len(chosen_moods))
        new_playlist_words.append(chosen_moods[rand_index])
        chosen_moods.remove(chosen_moods[rand_index])

    name_split = daylist_dict['name'].split()
    time_of_day = name_split[len(name_split) - 1]
    day_of_week = name_split[len(name_split) - 2]

    return (f'{new_playlist_words[0]} {day_of_week}s for {new_playlist_words[1]} {time_of_day}s featuring'
            f' {new_playlist_words[2]} vibes')


def generate_playlist(daylist_dict, hrefs, songs_per_mood, ):
    """ Creates a pseudorandom playlist based on the different key-words moods the user has chosen and their
    associated 'mix' playlist as well as the 'daylist' """
    new_playlist = []

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

    return new_playlist


@app.route('/', methods=['GET', 'POST'])
def home():
    """ Renders home route.
    When the user first enters the page, get their current Spotify daylist and associated mood tags.
    When the user generates a new playlist, take user choices for number of songs and mood tags and create new
    playlist """
    if request.method == 'GET':
        daylist_dict = get_playlist(DAYLIST)

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
        daylist_dict = get_playlist(DAYLIST)

        songs_per_mood = int(request.form.get('num_songs'))
        seed_playlists = request.form.getlist('selected_assets')
        seed_playlists = [tuple(item.split('|')) for item in seed_playlists]

        hrefs = [href for href, word in seed_playlists]
        chosen_moods = [word for href, word in seed_playlists]
        new_playlist_name = generate_playlist_name(chosen_moods, daylist_dict)

        new_playlist = generate_playlist(daylist_dict, hrefs, songs_per_mood)

        sp.user_playlist_create(
            user=USERNAME,
            name=new_playlist_name,
            public=False,
            collaborative=False,
            description="randomly generated from daylist mixes and spotify's api"
        )

        new_playlist_dict = get_playlist(new_playlist_name)
        song_uris = [song['track']['uri'] for song in new_playlist]

        sp.playlist_add_items(
            playlist_id=new_playlist_dict['id'],
            items=song_uris,
            position=None
        )

        return render_template('index.html',
                               daylist_info=daylist_dict,
                               new_playlist=new_playlist,
                               new_playlist_name=new_playlist_name)


@app.route('/play', methods=['POST'])
def play_song():
    """ Route to handle music playback when the user clicks on a song """
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
