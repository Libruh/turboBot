import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import MySQLdb
import datetime
import re
import asyncio
import sys
import random
import time
from config import *

# The connection and authentication with the database using logins specified
# in the config file. TODO: make this happen through an API endpoint.
connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase)
cursor = connection.cursor()

# Spotipy declaration and authentication
scope = 'playlist-modify-public'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(spotiClientID,spotiClientSecret, spotiRedirect, scope=scope))

# Bot declaration and authentication, as well as slash command registration 
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

# FUNCTIONS
def resetConnection():
    global connection
    global cursor
    connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase )
    cursor = connection.cursor()

# getContributor and inPlaylist have been combined into one function
def getContributors(trackIDs):
    resetConnection()
    query = "SELECT `trackID`,`addedBy` from "+dbTable+" WHERE `trackID` IN (" + ", ".join(f"'{trackID}'" for trackID in trackIDs) + ")"
    try:
        cursor.execute(query)
        connection.commit()
    except Exception as e:
        connection.rollback()
    data = cursor.fetchall()
    parsedDict = dict((x, y) for x, y in data)
    return parsedDict

# adds a list of trackIDs to the database and attributes them to addedBy
def db_addTracks(trackIDs, addedBy):
    resetConnection()
    today = datetime.date.today()
    playlistDate = today - datetime.timedelta(days=today.weekday())
    query = "INSERT INTO "+dbTable+" (`trackID`, `playlistDate`,`addedBy`,`season`) VALUES "
    for trackID in trackIDs:
        query = query + "('" + trackID + "','" + str(playlistDate) + "','" + str(addedBy) + "',"+curSeason+"),"
    query = query[:-1] + ";"
    try:
        cursor.execute(query)
        connection.commit()
    except:
        connection.rollback()

def db_removeTrack(trackID):
    resetConnection()
    query = "DELETE FROM "+dbTable+" WHERE `trackID` = '"+trackID+"';"
    print(query)
    try:
        cursor.execute(query)
        connection.commit()
    except Exception as e:
        print(e)
        connection.rollback()

# adds specified tracks to the standard playlists and then calls db_addTracks
def addTracks(trackIDs, addedBy):
    sp.playlist_add_items(weeklyPlaylist, trackIDs)
    sp.playlist_add_items(foreverPlaylist, trackIDs)
    db_addTracks(trackIDs, addedBy)
    
# removes specified tracks to the standard playlists and then calls db_removeTracks
def removeTrack(trackID):
    sp.playlist_remove_all_occurrences_of_items(weeklyPlaylist, trackIDs)
    sp.playlist_remove_all_occurrences_of_items(foreverPlaylist, trackIDs)
    db_removeTrack(trackID)
    

def getRecent():
    query = "SELECT * FROM "+dbTable+" ORDER BY `entryNum` DESC LIMIT 10"
    resetConnection()
    cursor.execute(query)
    connection.commit()
    return cursor.fetchall()

def convertTuple(tup):
    str =  ''.join(tup) 
    return str

def IDfromURL(url):
    if type(url) is tuple:
        url = convertTuple(url)
    trackID = url.split('/track/')[1]
    trackID = trackID.split('?')[0]
    return trackID

def getLeaderboard(season):
    leaderboard = {}
    query = "SELECT `addedby`,`votes` FROM "+dbTable
    if season != 0:
        query += " WHERE `season`="+str(season)
    resetConnection()
    cursor.execute(query)
    result = cursor.fetchall()
    for data in result:
        if data[0] != None:
            userID = data[0]
            votes = data[1]
            if userID not in leaderboard.keys():
                leaderboard[userID] = 0
            leaderboard[userID] = leaderboard[userID] + votes

    sortedLeaderboard = {}
    sortedLeaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    return sortedLeaderboard
    
def amendTrackID(oldID, newID):
    query = "UPDATE "+dbTable+" SET trackID = '"+newID+"' WHERE trackID = '"+oldID+"';"
    print(query)
    try:
        cursor.execute(query)
        connection.commit()
        print("changed")
    except Exception as e:
        print(e)
        connection.rollback(0)

def logVote(trackID, userID):
    time2log = time.strftime('%Y-%m-%d %H:%M:%S')

    query = "INSERT INTO "+voteTable+" (`authorID`, `trackID`,`datetime`) VALUES ('" + str(userID) + "','" + str(trackID) + "','"+str(time2log)+"')"
    print(query)
    try:
        cursor.execute(query)
        connection.commit()
    except:
        connection.rollback()

def hasVoted(trackID, userID):
    query = "SELECT * FROM "+voteTable+" WHERE authorID = '" + str(userID) + "' AND trackID = '" + str(trackID) + "';"

    try:
        cursor.execute(query)
        connection.commit()
        result = cursor.fetchone()
    except Exception as e:
        print(e)
        connection.rollback()
        return

    if (result == None):
        return False
    else:
        return True
    
async def voteTrack(ctx, trackID):
    memberID = ctx.author.id
    track = sp.track(trackID, 'US')

    curGuild = ctx.guild.id
    for guild in bot.guilds:
        if guild.id == curGuild:
            break

    voteReturn = None

    pullquery = "SELECT `votes`,`addedBy` from "+dbTable+" WHERE `trackID` = '"+trackID+"'"
    votequery = "UPDATE "+dbTable+" SET `votes` = `votes` + 1 WHERE `trackID` = '"+trackID+"'"
    resetConnection()
    try:
        cursor.execute(pullquery)
        connection.commit()
        voteReturn = cursor.fetchone()
    except Exception as e:
        print(e)
        connection.rollback()
        return

    if str(ctx.author.id) == voteReturn[1]:
        embed=discord.Embed(title="You can't vote for your own track!", description="No matter how bad you want to...", color=0xD8000C)
        embed.set_author(name= ctx.author.display_name + " tried to vote for a track", icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=track['album']['images'][1]['url'])
        return embed

    alreadyVoted = hasVoted(trackID, memberID)
    if alreadyVoted:
        embed=discord.Embed(title="You already voted for this track!", description="Your vote was not counted.", color=0xD8000C)
        embed.set_author(name= ctx.author.display_name + " tried to vote for a track", icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=track['album']['images'][1]['url'])
        return embed

    try:
        cursor.execute(votequery)
        connection.commit()
    except Exception as e:
        print(e)
        connection.rollback()
        return

    authorName, authorAvatar, contributorName = '', '', ''
    found1, found2 = False, False

    for member in guild.members:
        if str(member.id) == str(memberID):
            authorName = member.display_name
            authorAvatar = member.avatar_url
            found1 = True
        if str(member.id) == str(voteReturn[1]):
            contributorName = member.display_name
            found2 = True
        if found1 and found2:
            break

    if voteReturn[0] == 0:
        embedTitle = "This track now has " + str(voteReturn[0]+1) + " vote"
    else:
        embedTitle = "This track now has " + str(voteReturn[0]+1) + " votes"

    embed=discord.Embed(title=track['artists'][0]['name']+" - "+track['name'], description=embedTitle, color=0x1DB954)
    embed.set_author(name= authorName + " upvoted " + contributorName + "'s track", icon_url=authorAvatar)
    embed.set_thumbnail(url=track['album']['images'][1]['url'])

    logVote(trackID, str(memberID))

    return embed

URLregex = "(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@slash.slash(name="ping", guild_ids=serverIDs,
            description="Every good bot has a ping command!"
)
async def _ping(ctx): # Defines a new "context" (ctx) command called "ping."
    await ctx.send(f"Pong! ({bot.latency*1000}ms)")

@slash.slash(name="vote", guild_ids = serverIDs,
            description="Vote for a track by supplying it's spotify link, defaults to last track if none supplied",
            options=[
                create_option(
                    name="link",
                    description="a Spotify track link",
                    option_type=3,
                    required=False
                )
            ]
)

async def _vote(ctx, link: str=None):
    trackID = None
    if link is None:
        recentTracks = getRecent()
        trackID = recentTracks[0][0]
    else:
        trackID = IDfromURL(link)

    embed = await voteTrack(ctx, trackID)
    await ctx.send(embed=embed)

@slash.slash(name="remove", guild_ids = serverIDs,
        description="Remove a track by supplying it's spotify link, defaults to last track if none supplied",
        options=[
            create_option(
                name="link",
                description="a Spotify track link",
                option_type=3,
                required=False
            )
        ]
)
async def _remove(ctx, link: str=None):
    curGuild = ctx.guild.id
    for guild in bot.guilds:
        if guild.id == curGuild:
            break

    trackID = None
    if link is None:
        recentTracks = getRecent()
        trackID = recentTracks[0][0]
    else:
        trackID = IDfromURL(link)

    track = sp.track(trackID, 'US')

    embed=discord.Embed(title=track['artists'][0]['name']+" - "+track['name'], description="React to approve or deny this dialog")
    embed.set_author(name= "Are you sure you want to remove this track?")
    embed.set_thumbnail(url=track['album']['images'][1]['url'])
    removeMessage = await ctx.send(embed=embed)

    answers = ["✅","❌"]
    for reaction in answers:
        await ctx.message.add_reaction(emoji=reaction)
    
    def check(reaction, user):
        if str(reaction.emoji) in answers and user.id == ctx.author.id:
            return user == ctx.author and str(reaction.emoji) == str(reaction.emoji)

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=20.0, check=check)
        if(str(reaction)=="❌"):
            await removeMessage.delete()
        if(str(reaction)=="✅"):
            for member in guild.members:
                if str(member.id) == str(ctx.author.id):
                    authorName = member.display_name
                    break

            embed=discord.Embed(title=track['artists'][0]['name']+" - "+track['name'])
            embed.set_author(name=authorName+" removed a track.")
            embed.set_thumbnail(url=track['album']['images'][1]['url'])

            removeTrack(trackID)
            await removeMessage.clear_reactions()
            await removeMessage.edit(embed=embed)

    except Exception as e:
        print(e)
        await removeMessage.delete()

@slash.slash(name="leaderboard", guild_ids = serverIDs,
            description="Check the leaderboard",
            options=[
                create_option(
                    name="season",
                    description="the season you want to view, enter \"0\" to see all-time.",
                    option_type=4,
                    required=False
                )
            ]
)

async def _leaderboard(ctx, season: str=curSeason):
    leaderboard = getLeaderboard(season)
    embedData = []

    curGuild = ctx.guild.id
    for guild in bot.guilds:
        if guild.id == curGuild:
            break

    for i in range(0,6):
        if i > len(leaderboard)-1:
            break
        entry = leaderboard[i]
        found = False
        for member in guild.members:
            if str(member.id) == str(entry[0]):
                found = True
                embedData.append(member)
                break
        if not found:
            memberData = await bot.fetch_user(entry[0])
            embedData.append(memberData)
    
    if season != 0:
        boardTitle = "Season "+season
    else:
        boardTitle="All-Time"
    embed=discord.Embed(title=boardTitle, description="Our top voted contributors")
    embed.set_thumbnail(url=embedData[0].avatar_url)
    for i in range(0,5):
        if i > len(embedData)-1:
            break
        member = embedData[i]
        embed.add_field(name=str(i+1)+". "+member.display_name, value=str(leaderboard[i][1])+" votes", inline=False)

    await ctx.send(embed=embed)

@slash.slash(name="votelist", guild_ids = serverIDs,
            description="Vote from a list of recent tracks",
            options = []
)
async def _votelist(ctx):
    curGuild = ctx.guild.id
    for guild in bot.guilds:
        if guild.id == curGuild:
            break

    embed=discord.Embed(title="Loading List...", description="One moment")
    votelistMessage = await ctx.send(embed=embed)
    
    recentTracks = getRecent()
    recentTracks= recentTracks[0:9]
    
    embed=discord.Embed(title="Send a number to vote for that song!", description="This dialogue will expire in 20s")

    trackIDs = [track[0] for track in recentTracks]
    contributorDict = getContributors(trackIDs)
    displayDict = {}

    for trackID in contributorDict:
        for member in guild.members:
            if str(member.id) == str(contributorDict[trackID]):
                displayDict[trackID] = member.display_name
                break

    spotifyData = sp.tracks(trackIDs, 'US')

    embed=discord.Embed(title="React with a number to vote for that track!", description="This dialogue will expire in 20s")
    
    index=0

    for track in spotifyData['tracks']:
        index += 1
        namevar = '{index}. {name} - {artist} '.format(index=index, name=str(track['name']), artist=str(track['artists'][0]['name']))
        valuevar = ''
        try:
            valuevar = 'added by {name}'.format(name=displayDict[str(track['id'])])
        except KeyError:
            amendTrackID(trackIDs[index-1], str(track['id']))
            valuevar = 'added by {name}'.format(name=displayDict[trackIDs[index-1]])
        except Exception as e:
            print("Error other than KeyError thrown", e)
        embed.add_field(name=namevar, value=valuevar, inline=False)

    numbers = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    for reaction in numbers:
        await ctx.message.add_reaction(emoji=reaction)

    await votelistMessage.edit(embed=embed)
    
    def check(reaction, user):
        if str(reaction.emoji) in numbers and user.id == ctx.author.id:
            return user == ctx.author and str(reaction.emoji) == str(reaction.emoji)
            
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=20.0, check=check)
        trackID = spotifyData['tracks'][numbers.index(str(reaction))]['id']
        embed = await voteTrack(ctx, trackID)
        await votelistMessage.edit(embed=embed)
        await votelistMessage.clear_reactions()
    except Exception as e:
        print(e)
        await votelistMessage.delete()

    return

@bot.event
async def on_message(message):
    global urls
    global lastmessage
    global votetrack
    global tracklistMsg
    global votetracks
    global removeList

    if message.author == bot.user:
        return

    if "https://open.spotify.com/track" in str(message.content) and not message.content.startswith("/"):
        curGuild = message.guild.id
        for guild in bot.guilds:
            if guild.id == curGuild:
                break
        
        urls = re.findall(URLregex, message.content)
        addTrackIDs = []
        trackIDs = []
        for url in urls: trackIDs.append(IDfromURL(url))
        contributorDict = getContributors(trackIDs)
        for trackID in trackIDs:
            if trackID not in contributorDict:
                addTrackIDs.append(trackID)
            else:
                track = sp.track(trackID, 'US')
                displayName = ''
                avatar = ''
                if not contributorDict[trackID] == "":
                    for member in guild.members:
                        if str(member.id) == str(contributorDict[trackID]):
                            displayName = member.display_name
                            avatar = member.avatar_url
                            break

                embed=discord.Embed(title=track['name'] + " - "+track['artists'][0]['name'])
                if displayName != "":
                    if member.id == message.author.id:
                        embed.set_author(name= "You already submitted this!", icon_url=avatar)
                    else:
                        embed.set_author(name= displayName + " "+random.choice(alreadyQuips), icon_url=avatar)
                    embed.description=("has already been submitted")
                    embed.set_thumbnail(url=track['album']['images'][1]['url'])
                else:
                    embed.set_author(name="Someone "+random.choice(alreadyQuips), icon_url="https://github.com/Libruh/turboWeb/blob/master/src/img/misc/emptyalbum.png?raw=true")
                    embed.description=("has already been submitted")
                await message.add_reaction("❌")
                await message.channel.send(embed=embed)
        if len(addTrackIDs) > 0:
            addTracks(addTrackIDs, message.author.id)
            await message.add_reaction("✅")

bot.run(discordPasskey)