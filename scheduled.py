from config import *
import discord
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import MySQLdb
import datetime
import time
from pprint import pprint

# The connection and authentication with the database using logins specified
# in the config file. TODO: make this happen through an API endpoint.
connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase)
cursor = connection.cursor()

# Spotipy declaration and authentication
scope = 'playlist-modify-public'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(spotiClientID,spotiClientSecret, spotiRedirect, scope=scope))

# Bot declaration and authentication, as well as slash command registration 
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

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

def weeklyRepair():
    outTracks = sp.playlist_tracks(weeklyPlaylist, fields='items.track.id', limit=100, offset=0, market=None, additional_types=('track', ))
    outTracks = [item['track']['id'] for item in outTracks['items']]
    sp.playlist_remove_all_occurrences_of_items(weeklyPlaylist, outTracks)

    today = datetime.datetime.today()
    minRange = today + datetime.timedelta(days=-today.weekday())
    minRange = minRange.replace(hour=0, minute=0, second=0, microsecond=0)

    resetConnection()
    query = "SELECT trackID FROM "+dbTable+" WHERE `playlistDate` = '"+str(minRange)+"' ORDER BY entryNum ASC;"
    
    cursor.execute(query)
    trackList = cursor.fetchall()
    trackIDs = [trackSet[0] for trackSet in trackList]

    sp.playlist_add_items(weeklyPlaylist, trackIDs)

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

async def getTopUsers():
    today = datetime.datetime.today()

    minRange = today + datetime.timedelta(days=-today.weekday(), weeks=-1)
    minRange = minRange.replace(hour=0, minute=0, second=0, microsecond=0)

    maxRange = today + datetime.timedelta(days=-today.weekday())
    maxRange = maxRange.replace(hour=0, minute=0, second=0, microsecond=0)

    resetConnection()
    query = "SELECT authorID, trackID FROM "+voteTable+" WHERE `datetime` BETWEEN '"+str(minRange)+"' and '"+str(maxRange)+"' "
    cursor.execute(query)
    voteList = cursor.fetchall()

    searchIDs = [trackSet[1] for trackSet in voteList]
    searchIDstring = "("
    for searchID in searchIDs:
        searchIDstring += "\""+searchID+"\", "
    searchIDstring = searchIDstring[:-2]+")"


    query = "SELECT trackID FROM "+dbTable+" WHERE `playlistDate` = '"+str(minRange)+"' ORDER BY entryNum ASC;"
    cursor.execute(query)
    trackList = cursor.fetchall()
    trackIDs = [trackSet[0] for trackSet in trackList]
    lastWeekCount = len(trackIDs)

    query = "SELECT trackID, addedBy FROM "+dbTable+" WHERE `trackID` IN "+searchIDstring+";"
    cursor.execute(query)
    votedTracks = cursor.fetchall()

    votingUsers = [trackSet[0] for trackSet in voteList]
    votedUsers = [trackSet[1] for trackSet in votedTracks]

    def most_common(lst):
        return max(set(lst), key=lst.count)

    votingWinner = most_common(votingUsers)
    votedWinner = most_common(votedUsers)

    for guild in client.guilds:
        if guild.id == serverIDs[0]:
            break
    
    guildRoles = await guild.fetch_roles()
    roleDict = {}
    searchRoles = ["Top Voter", "Top Voted", "Turbo AF"]

    for role in guildRoles:
        if role.name in searchRoles:
            roleDict[role.name] = role
            for member in role.members:
                await member.remove_roles(role)
    
    memberDict = {}
    for member in guild.members:
        if len(memberDict.keys()) == 2:
            break
        if str(member.id) == votingWinner:
            memberDict[votingWinner] = member
        if str(member.id) == votedWinner:
            memberDict[votedWinner] = member

    guildEmojis = await guild.fetch_emojis()
    searchEmojis = ["red_pip", "blue_pip", "turbo"]

    emojiDict ={}
    for emoji in guildEmojis:
        if emoji.name in searchEmojis:
            emojiDict[emoji.name] = emoji

    redPip = emojiDict["red_pip"]
    bluePip = emojiDict["blue_pip"]
    turboEmoji = emojiDict["turbo"]

    embed=discord.Embed(title= "Weekly Reset", description= "Everything has been reset! Last week, you submitted **"+str(lastWeekCount)+"** songs", color=0xb54dff)

    if votingWinner == votedWinner:
        await memberDict[votingWinner].add_roles(roleDict["Turbo AF"])
        embed.add_field(name=f"{turboEmoji} **Top Voted** and **Top Voter** - **"+memberDict[votedWinner].display_name+"**", value="Both received and cast the most votes", inline=False)
    else:
        await memberDict[votingWinner].add_roles(roleDict["Turbo AF"])
        await memberDict[votedWinner].add_roles(roleDict["Turbo AF"])

        await memberDict[votingWinner].add_roles(roleDict["Top Voter"])
        await memberDict[votedWinner].add_roles(roleDict["Top Voted"])

        embed.add_field(name=f"{redPip} **Top Voted** - **"+memberDict[votedWinner].display_name+"**", value="Received the most votes", inline=False)
        embed.add_field(name=f"{bluePip} **Top Voter** - **"+memberDict[votingWinner].display_name+"**", value="Cast the most votes", inline=False)

    guildChannels = await guild.fetch_channels()
    commChannel = "music"
    for channel in guildChannels:
        if channel.name == commChannel:
            commChannel = channel

    await commChannel.send(embed=embed)

@client.event
async def on_ready():
    print('Logged on as {0.user}, beginning weekly tasks...'.format(client))
    # weeklyRepair()
    resetTop()
    resetShuffle()
    wipePlaylist(weeklyPlaylist)
    await getTopUsers()
    print("Tasks Complete.")
    await client.close()

client.run(discordPasskey)