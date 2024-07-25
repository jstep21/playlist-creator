import os
import re
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


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        current_playlists = sp.current_user_playlists()['items']
        daylist_playlist_id = None
        new_playlist_id = None
        description = ''
        daylist_name = ''
        daylist_image_url = ''
        current_user = sp.current_user()['id']

        # UNCOMMENT CODE BELOW TO SEE YOUR AVAILABLE AUDIO DEVICES FOR PLAYBACK
        # ADD THE DEVICE ID TO A "DEVICE_ID" ENVIRONMENT VARIABLE
        # devices = sp.devices()
        # print(devices)

        for playlist in current_playlists:
            if "daylist" in playlist['name']:
                daylist_playlist_id = playlist['id']
                description = playlist['description']
                daylist_name = playlist['name']
                daylist_image_url = playlist['images'][0]['url']
            # if playlist['name'] == 'new_playlist_name':

        if not daylist_playlist_id:
            return 'Daylist not found'

        anchor_words = re.findall(r'<a href="([^"]*)">([^<]*)</a>', description)
        current_daylist = sp.playlist_items(daylist_playlist_id)

        anchor_playlists = []
        for playlist, word in anchor_words:
            anchor_playlists.append(sp.playlist_items(playlist.split(':')[2]))

        songs = [song['track'] for song in current_daylist['items']]

        return render_template(template_name_or_list='index.html',
                               daylist_name=daylist_name,
                               description=description,
                               image_url=daylist_image_url,
                               songs=songs,
                               anchor_words=anchor_words,
                               anchor_playlists=anchor_playlists
                               )
    else:
        words_selected = request.form.getlist('selected_assets')
        return redirect(url_for('generate_playlist',
                                words=words_selected))


@app.route('/play', methods=['POST'])
def play_song():
    data = request.get_json()
    song_uri = data.get('song_uri')

    try:
        sp.transfer_playback(DEVICE_ID)
        sp.start_playback(uris=[song_uri])
        return jsonify(success=True)
    except Exception as e:
        print(e)
        return jsonify(success=False), 500


@app.route('/generate-playlist')
def generate_playlist(words):
    mood_tags = words
    return render_template('new-playlist.html')


if __name__ == "__main__":
    app.run(debug=True, port=5001)
