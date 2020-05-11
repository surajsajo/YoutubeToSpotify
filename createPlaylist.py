"""
Youtube to Spotify Playlist transfer

This class copies all the songs from a given youtube playlist and creates a new playlist by the same name and
adds all the songs it can find to the new Spotify Playlist.

The playlist that you would like to copy must be under the ownership of the youtube account you sign in with (you will
be asked to sign into your youtube account once you run the program).

0. Get Spotify Token
1. Log into Youtube
2. Grab Our Liked Videos
3. Create A New Playlist
4. Search for the Song
5. Add this song into the new spotify playlist

"""
import json
import secrets
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl
import spotipy

class CreatePlaylist:

    def __init__(self, nameOfPlaylist, description):
        """
        nameOfPlaylist: This is the name of the playlist on your specific youtube account. This is also the same name
                        that the Spotify Playlist will have
        description: This is the description that you would like the spotify playlist will have.
        """
        self.nameOfPlaylist = nameOfPlaylist
        self.description = description
        self.username = secrets.userid
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}
        self.sp = self.get_spotify_token()

    #0. Get Spotify Token
    def get_spotify_token(self):
        """
        This is the method that returns the spotify token that has permission to create playlists and add songs to
        the account of the user id specified in the secrets folder. This function uses all the information in secrets.
        """
        scope = "playlist-modify-public playlist-modify-private user-read-email user-library-modify playlist-read-private"
        token = spotipy.util.prompt_for_user_token(
            username=self.username,
            scope=scope,
            client_id=secrets.client_id,
            client_secret=secrets.client_secret,
            redirect_uri=secrets.redirect_uri
        )
        sp = spotipy.Spotify(auth=token)
        return sp



    #1. Log into Youtube
    def get_youtube_client(self):
        """
        This function returns the youtube client that we can use to retrieve the playlists and liked videos we want.
        This Function uses the client_secret.json file that can be retrieved from the youtube data api once you request
        an account.
        Most of the code in this function is retrieved from Youtube Data API example code.
        """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        # copied from Youtube Data API
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json" #YOUTUBE DATA API INFO (Can be downloaded from Youtube Data API account

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client

    #2. Grab Our Liked Videos (videos from chosen playlist) and create dict of those
    def get_liked_videos(self):
        """
        This function retrieves all the liked videos from the specified playlist (self.nameOfPlaylsit) on Youtube
        and searches for that song on Spotify and creates a dictionary with the song info including the Spotify URI
        which is used to add to our Spotify Playlist
        """
        request = self.youtube_client.playlists().list(
            part="snippet",
            mine=True
        )
        playlistid_ = 0
        response = request.execute()
        for item in response["items"]:
            if item["snippet"]["title"] == self.nameOfPlaylist:
                playlistid_ = item["id"]
        if playlistid_ == 0:
            raise
        request2 = self.youtube_client.playlistItems().list(
            part="snippet",
            playlistId=playlistid_,
            maxResults="50"
        )
        response = request2.execute()
        nextToken = response.get('nextPageToken')
        while('nextPageToken' in response):
            nextpage = self.youtube_client.playlistItems().list(
                part="snippet",
                playlistId=playlistid_,
                maxResults="50",
                pageToken=nextToken
            ).execute()
            response['items'] += nextpage['items']
            if 'nextPageToken' not in nextpage:
                response.pop('nextPageToken',None)
            else:
                nextToken = nextpage['nextPageToken']
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}"

            #use youtube_dl to collect the song name & artist name
            try:
                video = youtube_dl.YoutubeDL({}).extract_info(youtube_url,download=False)
            except:
                continue
            song_name= video["track"]
            artist = video["artist"]

            #save all important info
            songUri= self.get_spotify_uri(song_name,artist)
            if songUri != None:
                self.all_song_info[video_title] ={
                    "youtube_url": youtube_url,
                    "song_name": song_name,
                    "artist": artist,

                    #add the uri, easy to get song to put into playlist
                    "spotify_uri": self.get_spotify_uri(song_name,artist)
                }


    #3. Create A New Playlist
    def create_playlist(self):
        """
        This simply creates a new spotify playlist on the specified spotify account and returns the ID of that playlist
        """
        playlist=self.sp.user_playlist_create(user=self.username,name=self.nameOfPlaylist,description=self.description)
        return playlist['id']

    #4. Search for the Song
    def get_spotify_uri(self,song_name, artist):
        """
        This function searches for a song on Spotiy given the song name and artist and returns the Spotify URI for it.
        """
        query = f"track:{song_name} artist:{artist}"
        result = self.sp.search(q=query,limit=1,type='track')

        #only use the first song
        if len(result['tracks']['items']) > 0 and result['tracks']['items'][0]['artists'][0]['name'] == artist:
            uri = result['tracks']['items'][0]["uri"]
        else:
            uri = None

        return uri

    #5. Add this song into the new spotify playlist
    def add_song_to_playlist(self):
        """
        This function puts it all the the other functions together and does it all.
        """
        #populate our songs dictionary
        self.get_liked_videos()

        #collect all of uri
        uris = []
        for song,info in self.all_song_info.items():
            uris.append(info["spotify_uri"])

        #create a new playlist
        playlist_id = self.create_playlist()

        #add all songs into new playlist

        #Spotipy can only add 100 songs at a time to a playlist that is why this method is taken
        g = len(uris)
        if g > 100:
            s = 0
            e = 99
            while g > 100:
                self.sp.user_playlist_add_tracks(user=self.username, playlist_id=playlist_id,
                                                 tracks=uris[s:e])
                g -= 100
                s = e + 1
                e += 100
            self.sp.user_playlist_add_tracks(user=self.username, playlist_id=playlist_id,
                                             tracks=uris[s:])
        else:
            self.sp.user_playlist_add_tracks(user=self.username, playlist_id=playlist_id,
                                             tracks=uris)




