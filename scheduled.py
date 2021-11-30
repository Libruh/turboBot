from config import *
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import MySQLdb

# The connection and authentication with the database using logins specified
# in the config file. TODO: make this happen through an API endpoint.
connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase)
cursor = connection.cursor()

# Spotipy declaration and authentication
scope = 'playlist-modify-public'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(spotiClientID,spotiClientSecret, spotiRedirect, scope=scope))

def resetConnection():
    global connection
    global cursor
    connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase )
    cursor = connection.cursor()

def wipePlaylist(playlistID):
    outTracks = sp.playlist_tracks(playlistID, fields='items.track.id', limit=100, offset=0, market=None, additional_types=('track', ))
    outTracks = [item['track']['id'] for item in outTracks['items']]
    sp.playlist_remove_all_occurrences_of_items(playlistID, outTracks)

def getRandom():
    query = "SELECT * FROM "+dbTable+" ORDER BY RAND() LIMIT "+playlistSize
    resetConnection()
    cursor.execute(query)
    connection.commit()
    return cursor.fetchall()

def getTop():
    query = "SELECT * FROM "+dbTable+" ORDER BY `votes` DESC, `entryNum` DESC LIMIT "+playlistSize
    resetConnection()
    cursor.execute(query)
    connection.commit()
    return cursor.fetchall()

def resetShuffle():
    wipePlaylist(shufflePlaylist)
    newTracks = getRandom()
    inTracks = [item[0] for item in newTracks]
    sp.playlist_add_items(shufflePlaylist, inTracks)

def resetTop():
    wipePlaylist(topPlaylist)
    newTracks = getTop()
    inTracks = [item[0] for item in newTracks]
    sp.playlist_add_items(topPlaylist, inTracks)    

resetTop()
resetShuffle()
wipePlaylist(weeklyPlaylist)