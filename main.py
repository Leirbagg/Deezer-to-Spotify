from flask import Flask, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import requests

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = "random_secret_key"
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

# Configuration OAuth pour Spotify
SPOTIPY_CLIENT_ID = "f465d4838f3e454786b3b482c5e09f73"
SPOTIPY_CLIENT_SECRET = "0b2881f6196448259acba9f7f87c885b"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "playlist-modify-public"

DEEZER_PLAYLIST_ID = "9472036242"

# Configuration de l'authentification OAuth
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=SCOPE)

# Fonction pour récupérer la playlist Deezer
def get_deezer_playlist(playlist_id):
    url = f"https://api.deezer.com/playlist/{playlist_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Fonction pour extraire les informations des pistes Deezer
def extract_tracks_from_deezer(playlist_data):
    tracks = []
    for track in playlist_data['tracks']['data']:
        track_info = {
            'title': track['title'],
            'artist': track['artist']['name'],
            'album': track['album']['title']
        }
        tracks.append(track_info)
    return tracks

# Fonction pour rechercher une piste sur Spotify
def search_spotify_track(sp, track_info):
    query = f"track:{track_info['title']} artist:{track_info['artist']}"
    result = sp.search(q=query, type='track', limit=1)
    if result['tracks']['items']:
        return result['tracks']['items'][0]['id']
    return None

# Route principale : redirection vers l'URL d'autorisation Spotify
@app.route('/')
def index():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# Route pour gérer le callback après l'authentification
@app.route('/callback')
def callback():
    # Capture le code d'authentification retourné par Spotify
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)

    # Stocker le token d'accès dans la session
    session["token_info"] = token_info
    return redirect(url_for('create_playlist'))

# Route pour créer une playlist après authentification
@app.route('/create_playlist')
def create_playlist():
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect('/')

    # Initialiser l'instance Spotipy avec le token d'accès
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Obtenir l'utilisateur authentifié
    user_info = sp.me()
    user_id = user_info['id']

    # Récupérer la playlist Deezer
    deezer_playlist_id = DEEZER_PLAYLIST_ID
    deezer_playlist = get_deezer_playlist(deezer_playlist_id)
    if not deezer_playlist:
        return "Erreur lors de la récupération de la playlist Deezer"

    # Extraire les pistes de la playlist Deezer
    deezer_tracks = extract_tracks_from_deezer(deezer_playlist)

    # Créer une nouvelle playlist sur Spotify
    playlist_name = deezer_playlist['title'] + " (from Deezer)"
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
    playlist_id = playlist['id']

    # Chercher chaque piste Deezer sur Spotify et les ajouter à la playlist
    spotify_track_ids = []
    for track in deezer_tracks:
        spotify_track_id = search_spotify_track(sp, track)
        if spotify_track_id:
            spotify_track_ids.append(spotify_track_id)

    if spotify_track_ids:
        sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist_id, tracks=spotify_track_ids)
        return f"Playlist '{playlist_name}' créée avec succès et {len(spotify_track_ids)} titres ajoutés !"
    else:
        return "Aucun titre n'a pu être ajouté à la playlist Spotify."

# Lancer le serveur Flask
if __name__ == '__main__':
    app.run(port=8888)
