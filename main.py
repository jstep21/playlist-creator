import os
import re
from random import randrange
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from flask import Flask, request, render_template, url_for, session, redirect, jsonify
# import logging
#
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")

# DEVICE_ID = os.environ.get("DEVICE_ID")
DAYLIST = 'daylist'
SCOPE = ('user-library-read playlist-modify-public playlist-modify-private streaming playlist-read-private '
         'user-read-playback-state user-modify-playback-state')

TOKEN_INFO = 'token_info'

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
    token_info = create_spotify_oauth().get_access_token(code)

    if token_info:
        session[TOKEN_INFO] = token_info
        return redirect(url_for('home'))
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

    try:
        daylist_dict = get_playlist(sp, 'daylist')
        if not daylist_dict:
            print('Daylist not found')
            return 'Daylist not found'

        if request.method == 'GET':

            # UNCOMMENT CODE BELOW TO SEE YOUR AVAILABLE AUDIO DEVICES FOR PLAYBACK
            # ADD THE DEVICE ID TO A "DEVICE_ID" ENVIRONMENT VARIABLE
            # devices = sp.devices()
            # print(devices)

            try:
                daylist_id = daylist_dict['id']

                current_daylist = sp.playlist_items(daylist_id)
                songs = [song['track'] for song in current_daylist['items']]

                anchor_words = re.findall(r'<a href="([^"]*)">([^<]*)</a>', daylist_dict['description'])
                anchor_playlists = []
                for playlist, word in anchor_words[:]:
                    try:
                        anchor_playlists.append(sp.playlist_items(playlist.split(':')[2]))
                    except SpotifyException as e:
                        print(f"Error with one of the {word} playlists. Error: {e}")
                        anchor_words.remove((playlist, word))

                return render_template(template_name_or_list='index.html',
                                       daylist_info=daylist_dict,
                                       songs=songs,
                                       anchor_words=anchor_words,
                                       anchor_playlists=anchor_playlists
                                       )
            except SpotifyException as e:
                print(f'Spotify API error: {e}')
                return "Error with Spotify's API"
            except Exception as e:
                print(f'Unexpected error occured: {e}')
                return 'An error occurred while processing your request'

        # For POST requests
        else:
            try:
                songs_per_mood = 10
                seed_playlists = request.form.getlist('selected_assets')
                seed_playlists = [tuple(item.split('|')) for item in seed_playlists]

                hrefs = [href for href, word in seed_playlists]
                chosen_moods = [word for href, word in seed_playlists]

                new_playlist_name = generate_playlist_name(chosen_moods, daylist_dict)
                new_playlist = generate_playlist(sp, daylist_dict, hrefs, songs_per_mood)

                sp.user_playlist_create(
                    user=sp.current_user()['id'],
                    name=new_playlist_name,
                    public=False,
                    collaborative=False,
                    description="randomly generated using daylist mixes and spotify's api"
                )

                new_playlist_dict = get_playlist(sp, new_playlist_name)
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
            except SpotifyException as e:
                print(f"Spotify API error during playlist creation: {e}")
                return 'Spotify API error during playlist creation'
            except Exception as e:
                print(f"Unexpected error occurred during POST request: {e}")
                return 'An error occurred while processing your request'
    except SpotifyException as e:
        print(f"Spotify API error: {e}")
        return 'Spotify API error'
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        return 'An error occurred while processing your request'


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
        scope=SCOPE
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

    # token_info = session.get(TOKEN_INFO, None)
    # if not token_info:
    #     print('Token not found, redirecting to login...')
    #     return redirect(url_for('login'))
    #
    # token_info = create_spotify_oauth().validate_token(token_info)
    # if not token_info:
    #     print('Token validation failed, redirecting to login...')
    #     return redirect(url_for('login'))
    #
    # session['TOKEN_INFO'] = token_info
    # return token_info


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
    time_of_day = name_split[len(name_split) - 1]
    day_of_week = name_split[len(name_split) - 2]

    return (f'{new_playlist_words[0]} {day_of_week}s for {new_playlist_words[1]} {time_of_day}s featuring'
            f' {new_playlist_words[2]} vibes')


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


if __name__ == "__main__":
    app.run(debug=True)
