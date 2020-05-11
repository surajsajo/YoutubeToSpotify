from createPlaylist import CreatePlaylist

"""
Run this main and it creates the new playlist and completes the task!
"""
nameOfPlaylist = "NAME OF YOUTUBE PLAYLIST YOU WANT TO COPY GOES HERE"
description = "DESCRIPTION GOES HERE"
new = CreatePlaylist(nameOfPlaylist,description)
new.add_song_to_playlist()