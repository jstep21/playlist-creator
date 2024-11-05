from spotipy.cache_handler import CacheHandler


class SessionClassHandler(CacheHandler):
    def __init__(self, session_key):
        self.session_key = session_key

    def get_cached_token(self):
        return session.get(self.session_key)