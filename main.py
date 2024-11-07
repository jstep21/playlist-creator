import os
import re
from random import randrange, shuffle
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from spotipy.cache_handler import CacheHandler
from flask import Flask, request, render_template, url_for, session, redirect, jsonify, flash


SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")

# DEVICE_ID = os.environ.get("DEVICE_ID")
DAYLIST = 'daylist'
SCOPE = ('streaming user-read-email user-library-read user-read-private playlist-modify-public '
         'playlist-modify-private playlist-read-private user-read-playback-state user-modify-playback-state '
         'user-top-read user-read-recently-played')

# SCOPE = 'streaming user-read-email user-read-private'

TOKEN_INFO = 'token_info'

DAYS_OF_THE_WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
TIME_OF_DAYS = ['morning', 'afternoon', 'evening', 'night', 'early', 'late']

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'


@app.route('/')
def login():
    if TOKEN_INFO in session:
        return redirect(url_for('home'))
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)


@app.route('/redirect')
def redirect_page():
    session.clear()
    code = request.args.get('code')

    if code:
        try:
            token_info = create_spotify_oauth().get_access_token(code, check_cache=False)
            session[TOKEN_INFO] = token_info
            return redirect(url_for('home'))
        except Exception as e:
            print(f"Error retrieving access token: {e}")
            return 'Error retrieving access token', 500
    else:
        print('Error retrieving access token')
        return 'Error retrieving access token', 500


@app.route('/home', methods=['GET', 'POST'])
def home():
    """ Renders home route.
    When the user first enters the page, get their current Spotify daylist and associated mood tags.
    When the user generates a new playlist, take user choices for number of songs and mood tags and create a new
    playlist """
    try:
        token_info = get_token()
    except OSError:
        print('User not logged in')
        return redirect("/")

    if not isinstance(token_info, dict):
        print('Invalid token information')
        return redirect("/")

    sp = spotipy.Spotify(auth=token_info['access_token'])

    # try:
    daylist_dict = get_playlist(sp, 'daylist')
    if not daylist_dict:
        print('Daylist not found')
        return 'Daylist not found'
    # except SpotifyException as e:
    #     print(f'Daylist not found: {e}')

    if request.method == 'GET':

        daylist_id = daylist_dict['id']

        current_daylist = sp.playlist_items(daylist_id)
        songs = [song['track'] for song in current_daylist['items']]

        top_artists = sp.current_user_top_artists(time_range="medium_term")

        # devices = sp.devices()

        anchor_words = re.findall(r'<a href="([^"]*)">([^<]*)</a>', daylist_dict['description'])
        anchor_playlists = []
        for playlist, word in anchor_words[:]:
            try:
                anchor_playlists.append(sp.playlist_items(playlist.split(':')[2]))
            except SpotifyException as e:
                print(f"Error with the {word} mix playlist. Error: {e}")
                anchor_words.remove((playlist, word))

        return render_template(template_name_or_list='index.html',
                               daylist_info=daylist_dict,
                               songs=songs,
                               anchor_words=anchor_words,
                               anchor_playlists=anchor_playlists,
                               top_artists=top_artists
                               )

    # For POST requests
    else:
        songs_per_mood = 10
        seed_playlists = request.form.getlist('selected_assets')
        seed_playlists = [tuple(item.split('|')) for item in seed_playlists]

        if len(seed_playlists) < 3:
            flash('Please enter at least 3 mood tags', 'error')
            redirect(url_for('home'))
        else:

            hrefs = [href for href, word in seed_playlists]
            chosen_moods = [word for href, word in seed_playlists]

            new_playlist_name_desc = generate_playlist_name(chosen_moods, daylist_dict)

            sp.user_playlist_create(
                user=sp.current_user()['id'],
                name=new_playlist_name_desc['name'],
                public=False,
                collaborative=False,
                description=new_playlist_name_desc['description']
            )
            new_playlist_dict = get_playlist(sp, new_playlist_name_desc['name'])

            new_playlist = generate_playlist(sp, daylist_dict, hrefs, songs_per_mood)
            shuffle(new_playlist)
            song_uris = [song['track']['uri'] for song in new_playlist]

            sp.playlist_add_items(
                playlist_id=new_playlist_dict['id'],
                items=song_uris,
                position=None
            )

            # flash('Playlist created successfully!', 'success')

            return render_template('index.html',
                                   daylist_info=daylist_dict,
                                   new_playlist=new_playlist,
                                   new_playlist_name=new_playlist_name_desc['name'],
                                   new_playlist_desc=new_playlist_name_desc['description'])
    #
    # except SpotifyException as e:
    #     print(f"Spotify API error: {e}")
    #     return 'Spotify API error'
    # except Exception as e:
    #     print(f"Unexpected error occurred: {e}")
    #     return 'An error occurred while processing your request'


# @app.route('/play', methods=['POST'])
# def play_song():
#     """ Route to handle music playback when the user clicks on a song """
#     token_info = get_token()
#     if isinstance(token_info, dict):
#         sp = spotipy.Spotify(auth=token_info['access_token'])
#         data = request.get_json()
#         song_uri = data.get('song_uri')
#
#         try:
#             sp.transfer_playback(DEVICE_ID)
#             sp.start_playback(uris=[song_uri])
#             return jsonify(success=True)
#         except Exception as e:
#             print(e)
#             return jsonify(success=False), 500


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
        cache_handler=SessionCacheHandler(TOKEN_INFO)
    )


def get_token():
    token_info = session.get(TOKEN_INFO)
    if not token_info:
        return None

    sp_oauth = create_spotify_oauth()

    try:
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session[TOKEN_INFO] = token_info
    except Exception as e:
        print(f'Error validating or refreshing token: {e}')
        return None

    return token_info


def get_playlist(sp, playlist_name):
    offset = 0
    playlist_dict = {}
    found = False

    while not found:
        try:
            current_playlists = sp.current_user_playlists(offset=offset)['items']
        except SpotifyException as e:
            print(f'Error fetching user playlists: {e}')
            return redirect(url_for('home'))

        if not current_playlists:
            break

        for playlist in current_playlists:
            if playlist_name in playlist['name']:
                if playlist_name == 'daylist':
                    playlist_dict = {
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'description': playlist['description'],
                        'image': playlist['images'][0]['url']
                    }
                else:
                    playlist_dict = {
                        'id': playlist['id'],
                        'name': playlist['name']
                    }
                found = True
                break

        if not found:
            offset += 50

    return playlist_dict


def generate_playlist_name(chosen_moods, daylist_dict):
    """Create a name for the new playlist from the chosen moods"""
    new_playlist_words = []
 
    for i in range(3):
        rand_index = randrange(len(chosen_moods))
        new_playlist_words.append(chosen_moods[rand_index])
        chosen_moods.remove(chosen_moods[rand_index])

    name_split = daylist_dict['name'].split()

    day_of_week = ''
    time_of_day = []
    full_time_of_day = ''

    for word in name_split:
        if word in DAYS_OF_THE_WEEK:
            day_of_week = word
        if word in TIME_OF_DAYS:
            time_of_day.append(word)

    if len(time_of_day) == 2:
        full_time_of_day = time_of_day[0] + time_of_day[1]
    elif time_of_day:
        full_time_of_day = time_of_day[0]

    playlist_name_desc_dict = {
        'name': f'{day_of_week} {full_time_of_day} vibes: {new_playlist_words[0]}, {new_playlist_words[1]} and '
                f'{new_playlist_words[2]}',
        'description': f'let your {full_time_of_day} flow with these {new_playlist_words[1]} rhythms. this playlist '
                       f'combines a smooth blend of {new_playlist_words[2]} and {new_playlist_words[0]}'
    }

    return playlist_name_desc_dict


def generate_playlist(sp, daylist_dict, hrefs, songs_per_mood, ):
    """ Creates a pseudorandom playlist based on the different key-words moods the user has chosen and their
    associated 'mix' playlist as well as the 'daylist' """
    new_playlist = []

    chosen_playlist_ids = [href.split('st:')[1] for href in hrefs]
    chosen_playlist_ids.append(daylist_dict['id'])

    # chosen_playlist_items = [sp.playlist_items(playlist_id) for playlist_id in chosen_playlist_ids]
    chosen_playlist_items = []
    for playlist_id in chosen_playlist_ids:
        try:
            items = sp.playlist_items(playlist_id=playlist_id)
            if items is not None:
                chosen_playlist_items.append(items)
            else:
                print(f'Warning: No items found for playlist ID {playlist_id}')
        except SpotifyException as e:
            print(f'Error retrieving items for playlist ID {playlist_id}: {e}')
        except TypeError as e:
            print(f'Typeerror retrieving items for playlist ID {playlist_id}: {e}')

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


def get_users_audio_devices(sp):
    devices = sp.devices()
    return devices


class SessionCacheHandler(CacheHandler):
    def __init__(self, session_key):
        self.session_key = session_key

    def get_cached_token(self):
        return session.get(self.session_key)

    def save_token_to_cache(self, token_info):
        session[self.session_key] = token_info

    def delete_cached_token(self):
        session.pop(self.session_key, None)


if __name__ == "__main__":
    app.run(debug=True)
