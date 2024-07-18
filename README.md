# Spotify Playlist Creator



## Introduction


The goal of this project is to be able to generate a new playlist from a Spotify user's personalized daylist. Every 
Spotify user has access to their "daylist," an auto-generated playlist based on a user's listening habits at a 
specific time of day. 

Let's say I check my daylist on a Thursday morning, all the songs in it will be based on 
music I typically listen to at that time of day. As you can see below, there are key descriptive words associated 
with my Thursday morning listening habits, such as "ethereal pop" or "balearic beat."

<img src="static/images/daylist1.png" alt="front page">

These key-words, along with the songs in the daylist, are updated every few hours or so throughout the day. For this 
website, the user is able to click any of the key-words (shown in the bottom list next to "Show Daylist") and see a 
different playlist Spotify generates for that key-word(s). This is in addition to being able to show the user's 
current daylist with the "Show Daylist" button along the bottom list.

<img src="static/images/playlist1.png">

From here, the user is able to click on any song and hear it play through their chosen audio device, if you have it 
set up (more details below and in comments in <code>main.py</code>)

## Getting Started
### Prerequisites
<ul>
    <li>Pycharm, VSCode (add the Python extension) or any IDE for writing code in Python</li>
    <li>Have a Spotify account and log into <a href="https://developer.spotify.com/">Spotify for 
Developers</a> 
        <br> 
        <ul>
            <li>Go to your Dashboard and create a new app</li>
            <li>Add Client ID, Client Secret and Redirect URI to the project as environment variables</li>
            <li>Also add your Username and Device ID (Optional but needed for audio playback, see comments in 
<code>main.py</code> to find your audio device's id)
</li>
        </ul></li>
    <li>Flask installed in the Virtual Environment (<code>pip install flask</code>)</li>
    <li>Spotipy installed in the Virtual Environment (<code>pip install spotipy</code>)</li>
</ul>

### Installation

<h5>Clone this Repository</h5>
```commandline
git clone https://github.com/jstep21/playlist-creator.git
```

<h5>Install Necessary Packages</h5>

<h6>Flask</h6>
```commandline
pip install flask
```

<h6>Spotipy</h6>
```commandline
pip install spotipy
```

<h6>Requests</h6>
```commandline
pip install requests
```