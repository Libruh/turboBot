from spotipy.oauth2 import SpotifyOAuth
import discord
import spotipy
import json
import re
import MySQLdb
import datetime
import asyncio
from config import *

connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase )
cursor = connection.cursor()

scope = 'playlist-modify-public'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(spotiClientID,spotiClientSecret, spotiRedirect, scope=scope))

urls = []
votetracks = []
tracklistMsg = discord.message
removeList =[]

def checkConnection():
    global connection
    global cursor
    connection = MySQLdb.connect(dbAddr,dbUser,dbPass,dbDatabase )
    cursor = connection.cursor()

def convertTuple(tup): 
    str =  ''.join(tup) 
    return str

def inPlaylist(trackID):
    checkConnection()
    if (cursor.execute("SELECT * from `tracks` where `trackID` = '"+trackID+"'")):
        return True
    else:
        return False

def db_addTrack(trackID, addedBy):
    checkConnection()
    today = datetime.date.today()
    playlistDate = today - datetime.timedelta(days=today.weekday())
    query = "INSERT INTO `tracks` (`trackID`, `playlistDate`,`addedBy`) VALUES ('"+trackID+"', '"+str(playlistDate)+"', '"+addedBy+"')"
    try:
        cursor.execute(query)
        connection.commit()
    except:
        connection.rollback()

def db_removeTrack(trackID):
    checkConnection()
    query = "DELETE FROM `tracks` WHERE `trackID` = '"+trackID+"'"
    try:
        cursor.execute(query)
        connection.commit()
    except Exception as e:
        connection.rollback()
    
def IDfromURL(url):
    url = convertTuple(url)
    trackID = url.split('/track/')[1]
    trackID = trackID.split('?')[0]
    return trackID

def addTrack(trackID, addedBy):
    sp.playlist_add_items(weeklyPlaylist,[trackID]) #adds to the weekly playlist
    sp.playlist_add_items(foreverPlaylist,[trackID]) #adds to the forever playlist
    db_addTrack(trackID, addedBy)

def removeTrack(trackID):
    sp.playlist_remove_all_occurrences_of_items(weeklyPlaylist, [trackID])
    sp.playlist_remove_all_occurrences_of_items(foreverPlaylist, [trackID])
    db_removeTrack(trackID)

def getContributor(trackID):
    query = "SELECT `addedBy` from `tracks` WHERE `trackID` = '" + trackID + "'"
    checkConnection()
    cursor.execute(query)
    return cursor.fetchone()[0]

def upvoteTrack(trackID):
    query = "UPDATE `tracks` SET `votes` = `votes` + 1 WHERE `trackID` = '"+trackID+"'"
    checkConnection()
    try:
        cursor.execute(query)
        connection.commit()
        print(trackID + " upvoted")
    except Exception as e:
        print(e)
        connection.rollback()

def seasonalInPlaylist(trackID):
    checkConnection()
    if (cursor.execute("SELECT * from `seasonalTracks` where `trackID` = '"+trackID+"' AND `occasion` = '"+seasonalOccasion+"'")):
        return True
    else:
        return False

def seasonalGetContributor(trackID):
    query = "SELECT `addedBy` from `seasonalTracks` WHERE `trackID` = '" + trackID + "'"
    checkConnection()
    cursor.execute(query)
    return cursor.fetchone()[0]

def seasonalAddTrack(trackID, addedBy):
    checkConnection()
    query = "INSERT INTO `seasonalTracks` (`trackID`, `occasion`,`addedBy`) VALUES ('"+trackID+"', '"+seasonalOccasion+"', '"+addedBy+"')"
    try:
        cursor.execute(query)
        connection.commit()
        sp.playlist_add_items(seasonalPlaylist,[trackID]) #adds to the seasonal playlist
    except:
        connection.rollback()

def getRecent():
    query = "SELECT * FROM `tracks` ORDER BY `entryNum` DESC LIMIT 10"
    checkConnection()
    cursor.execute(query)
    return cursor.fetchall()

def getLeaderboard():
    leaderboard = {}
    query = "SELECT `addedby`,`votes` FROM `tracks`"
    checkConnection()
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

getLeaderboard()

votetrack = {}

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

URLregex = "(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"

@client.event
async def on_message(message):
    global urls
    global lastmessage
    global votetrack
    global tracklistMsg
    global votetracks
    global removeList

    if message.author == client.user:
        return

    if "https://open.spotify.com/track" in str(message.content) and not message.content.startswith(prefix):
        curGuild = message.guild.id
        for guild in client.guilds:
            if guild.id == curGuild:
                break
        lastmessage = message
        urls = re.findall(URLregex, message.content)
        for url in urls:
            trackID = IDfromURL(url)
            try:
                if not inPlaylist(trackID):
                    messageAuthor = str(message.author.id)
                    addTrack(str(trackID), messageAuthor)
                    await message.add_reaction("✅")
                else:
                    foctrack = sp.track(''.join(url))
                    contributorID = getContributor(trackID)
                    displayName = ''
                    for member in guild.members:
                        if str(member.id) == str(contributorID):
                            displayName = member.display_name
                            break
                    await message.add_reaction("❌")
                    if displayName != '':
                        await message.channel.send("**" + foctrack['name'] + "** has already been submitted by **"+displayName+"**!")
                    else:
                        await message.channel.send("**" + foctrack['name'] + "** has already been submitted")
                    upvoteTrack(trackID)
                        
            except Exception as e:
                print("ERROR: "+str(e))
                await message.add_reaction("❌")
                await message.channel.send("I couldn't find that track, is that a valid link?")

    if message.content.isdigit() and len(votetracks) != 0:
        if int(message.content) in list(range(1, 11)) and (message.channel == tracklistMsg.channel):
            removeList.append(message)

            curGuild = message.guild.id
            for guild in client.guilds:
                if guild.id == curGuild:
                    break

            trackID = votetracks[int(message.content)-1]
            trackUrl = 'https://open.spotify.com/track/'+str(trackID)

            foctrack = sp.track(trackUrl)
            contributorID = getContributor(trackID)
            contributorName = ''
            for member in guild.members:
                if str(member.id) == str(contributorID):
                    contributorName = member.display_name
                    break

            canVote = 'false'

            if message.author.display_name == contributorName:
                canVote='ownTrack'
            elif message.author.id in votetrack:
                if trackID not in votetrack[message.author.id]:
                    votetrack[message.author.id].append(trackID)
                    canVote = 'true'
                else:
                    canVote='alreadyVoted'
            else:
                votetrack[message.author.id] = [trackID]
                canVote = 'true'

            if canVote == 'ownTrack':
                tempm = await message.channel.send("You can't upvote your own track.")
                removeList.append(tempm)
            elif canVote == "true":
                upvoteTrack(trackID)
                await message.delete()
                await tracklistMsg.delete()
                votetracks = []

                if contributorName != '':
                    await message.channel.send("**"+message.author.display_name+"** upvoted **"+contributorName+"**'s track **"+ foctrack['name'] + " - " + foctrack['artists'][0]['name'] + "**!")
                else:
                    await message.channel.send("**"+message.author.display_name+"** upvoted **"+ foctrack['name'] + " - " + foctrack['artists'][0]['name'] + "**!")

                for message in removeList:
                    try:
                        await message.delete()
                    except:
                        pass

                removeList = []    

            elif canVote == "alreadyVoted":
                tempm = await message.channel.send("You've already upvoted this track!")
                removeList.append(tempm)
        else:
            await message.channel.send("Enter an index between 1 and 10!")

    if message.content.startswith(prefix+seasonalCommand) and inSeason:
        curGuild = message.guild.id
        for guild in client.guilds:
            if guild.id == curGuild:
                break
        lastmessage = message
        urls = re.findall(URLregex, message.content)
        for url in urls:
            trackID = IDfromURL(url)
            try:
                if not seasonalInPlaylist(trackID):
                    messageAuthor = str(message.author.id)
                    seasonalAddTrack(str(trackID), messageAuthor)
                    await message.add_reaction(seasonalConf)
                else:
                    foctrack = sp.track(''.join(url))
                    contributorID = seasonalGetContributor(trackID)
                    displayName = ''
                    for member in guild.members:
                        if str(member.id) == str(contributorID):
                            displayName = member.display_name
                            break
                    await message.add_reaction(seasonalDeny)
                    await message.channel.send(seasonalConf + " **" + foctrack['name'] + "** has already been submitted by **"+displayName+"**!")
            except Exception as e:
                print("ERROR: "+str(e))
                await message.add_reaction(seasonalDeny)
                await message.channel.send("I couldn't find that track, is that a valid link?")

    if message.content.startswith(prefix+"vote"):
        curGuild = message.guild.id
        for guild in client.guilds:
            if guild.id == curGuild:
                break

        if message.content != (prefix+"vote"):
            urls = re.findall(URLregex, message.content)
        elif len(urls) <= 0:
            await message.channel.send("No tracks logged, try specifying what track you want to vote for.")

        for url in urls:
            trackID = IDfromURL(url)
            foctrack = sp.track(''.join(url))
            contributorID = getContributor(trackID)
            contributorName = ''
            for member in guild.members:
                if str(member.id) == str(contributorID):
                    contributorName = member.display_name
                    break

            canVote = 'false'

            if message.author.display_name == contributorName:
                canVote='ownTrack'
            elif message.author.id in votetrack:
                if trackID not in votetrack[message.author.id]:
                    votetrack[message.author.id].append(trackID)
                    canVote = 'true'
                else:
                    canVote='alreadyVoted'
            else:
                votetrack[message.author.id] = [trackID]
                canVote = 'true'

            if canVote == 'ownTrack':
                await message.channel.send("You can't upvote your own track.")
            elif canVote == "true":
                upvoteTrack(trackID)
                await message.delete()
                if contributorName != '':
                    await message.channel.send("**"+message.author.display_name+"** upvoted **"+contributorName+"**'s track **"+ foctrack['name'] + " - " + foctrack['artists'][0]['name'] + "**!")
                else:
                    await message.channel.send("**"+message.author.display_name+"** upvoted **"+ foctrack['name'] + " - " + foctrack['artists'][0]['name'] + "**!")
            elif canVote == "alreadyVoted":
                await message.channel.send("You've already upvoted this track!")

    if message.content.startswith(prefix+"votelist"):
        try:
            await tracklistMsg.delete()
        except:
            print("no tracklist msg")
        votetracks = []
        recentTracks = getRecent()
        tracklist = "```nim\n"
        for index, track in enumerate(recentTracks):
            trackID = track[0]
            votetracks.append(trackID)

            trackUrl = 'https://open.spotify.com/track/'+str(trackID)
            foctrack = sp.track(trackUrl)
            cleanName = foctrack['name'].replace("'", "")

            tracklist = tracklist + str(index+1) + ") " + cleanName + " - " + foctrack['artists'][0]['name']+"\n\n"

        tracklist = tracklist + "respond with the index of the song you'd like to vote for!\nThis dialogue will time out in 20s\n```"
        
        tracklistMsg = await message.channel.send(tracklist)

        await asyncio.sleep(20)
        await tracklistMsg.delete()
        votetracks = []

        for msg in removeList:
            try:
                await msg.delete()
            except:
                pass

        removeList = []

    if message.content.startswith(prefix+"leaderboard"):
        leaderboard = getLeaderboard()
        embedData = []

        curGuild = message.guild.id
        for guild in client.guilds:
            if guild.id == curGuild:
                break

        for i in range(0,6):
            entry = leaderboard[i]
            for member in guild.members:
                        if str(member.id) == str(entry[0]):
                            embedData.append(member)
                            break


        embed=discord.Embed(title="Leaderboard", description="Our top voted contributors")
        embed.set_thumbnail(url=embedData[0].avatar_url)
        for i in range(0,5):
            member = embedData[i]
            embed.add_field(name=str(i+1)+". "+member.display_name, value=str(leaderboard[i][1])+" votes", inline=False)

        await message.channel.send(embed=embed)

    if message.content.startswith(prefix+"remove"):
        if message.content == (prefix+"remove"):
            if len(urls) > 0:
                for url in urls:
                    trackID = IDfromURL(url)
                    removeTrack(trackID)
                    foctrack = sp.track(''.join(url))
                    await lastmessage.remove_reaction("✅", client.user)
                    await message.delete()
                    await message.channel.send("**"+message.author.display_name+"** removed **" + foctrack['name'] + " - " + foctrack['artists'][0]['name'] + "**!")
            else:
                await message.channel.send("No tracks logged, try specifying what track you want to remove.")
        elif "https://open.spotify.com/track" in str(message.content):
            urls = re.findall(URLregex, message.content)
            for url in urls:
                try:
                    trackID = IDfromURL(url)
                    removeTrack(IDfromURL(url))
                    foctrack = sp.track(''.join(url))
                    await message.delete()
                    await message.channel.send("**"+message.author.display_name+"** removed **" + foctrack['name'] + " - " + foctrack['artists'][0]['name'] + "**!")
                except Exception as e:
                    await message.channel.send("`"+str(url)+"` is not a valid spotify track link.")

client.run(discordPasskey)