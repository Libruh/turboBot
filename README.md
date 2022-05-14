# TurboBot
The **Turbo Music Bot** started as a small tool to automatically take Spotify links sent to the discord `#music` channel into a Spotify playlist.
Over time, it became something much bigger. A place to share, discover, rate, and discuss music.
## Playlists
Any time a link is sent to the `#music` channel, Turbo Bot adds the track to a Spotify playlist, and makes a record of it in it's system.

### Turbo Weekly

<img align="left" width="100" height="100" src="./img/turboWeekly.jpg">

This playlist is the main place to find new music. new Tracks go directly here, and then are completely wiped every monday. 

<br />

### Turbo Shuffle

<img align="left" width="100" height="100" src="./img/turboShuffle.jpg">

Pulling from a massive archive, a completely random playlist is generated every monday, allowing you to find tracks you may have missed, or revisit old ones.

<br />

### Turbo Top

<img align="left" width="100" height="100" src="./img/turboTop.jpg">

The definitive track leaderboard. This playlist is kept up-to-date with the top voted tracks across the archive.

<br />

### Turbo Forever

<img align="left" width="100" height="100" src="./img/turboForever.jpg">

The archive of every song ever submitted. This playlist holds your favorite song, and your next favorite song too.

<br />

## Features

### Website

To make navigating Turbo's massive music library easier. [A website](https://turboaf.net) was made to view archives, user profiles, leaderboards, and place votes.

### Voting

Via either commands or Discord reactions, users are able to commend tracks via a built-in voting system. Users that earn votes enjoy a spot on the leaderboard, special server roles, and their tracks placed in [Turbo Top](#Turbo-Top) playlist.

### Seasons

Every six months, a new *season* begins. All leaderboards, votes, and roles are reset for that period of time. This way, old users can still compete on even ground with new ones!

### Refresh
We don't want to discourage re-visiting old favorites, but we also don't want finding a track first to lost it's importance. To fix this, instead of adding previously-seen songs as normal, they are **Refreshed**. This means that they will be added back into the weekly rotation, but all votes will be attributed to the original person to discover the track.

### Commands

- `/vote [link]`
    - Places a vote for the spotify link provided
- `/votelist`
    - Summons a menu to vote from a list of recent songs
- `/remove`
    - Removes a track from the archive, as if it never happened.
- `/leaderboard [season]`
    - View the leaderboard for a given season, or for all time!

