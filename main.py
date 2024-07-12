import os
import re
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from flask import Flask, request, render_template, url_for, session, redirect
#
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")
USERNAME = os.environ.get("USERNAME")

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == "GET":
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                                       client_secret=SPOTIPY_CLIENT_SECRET,
                                                       redirect_uri=SPOTIPY_REDIRECT_URI,
                                                       scope='user-library-read playlist-modify-public',
                                                       show_dialog=True,
                                                       cache_path='.cache',
                                                       username=USERNAME
                                                       ))

        current_playlists = sp.current_user_playlists()['items']
        daylist_playlist_id = None
        new_playlist_id = None
        description = ''
        daylist_name = ''
        daylist_image_url = ''
        current_user = sp.current_user()['id']

        for playlist in current_playlists:
            # print(playlist)
            if "daylist" in playlist['name']:
                daylist_playlist_id = playlist['id']
                description = playlist['description']
                daylist_name = playlist['name']
                daylist_image_url = playlist['images'][0]['url']
            # if playlist['name'] == 'new_playlist_name':

        if not daylist_playlist_id:
            return 'Daylist not found'

        anchor_words = re.findall(r'<a href="([^"]*)">([^<]*)</a>', description)
        # linked_descriptive_words = [word for href, word in anchor_words]
        # hrefs = [href for href, word in anchor_words]
        current_daylist = sp.playlist_items(daylist_playlist_id)

        song_uris = []
        for song in current_daylist['items']:
            song_uris.append(song['track']['uri'])

        songs = []

        for song in current_daylist['items']:
            songs.append(song['track'])

        return render_template(template_name_or_list='index.html',
                               daylist_name=daylist_name,
                               description=description,
                               image_url=daylist_image_url,
                               songs=songs,
                               anchor_words=anchor_words,
                               )


if __name__ == "__main__":
    app.run(debug=True, port=5000)