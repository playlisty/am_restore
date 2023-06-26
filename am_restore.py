#!/usr/bin/env python3
#
# This is a simple Python script which tries to re-create playlists from an 'Apple Media Services information' archive
#

import json
import zipfile
import io
import argparse
import csv

class PLTrack:

    def __init__(self, track):
        self.name = str(track["Title"])
        self.artist = track.get("Artist", "")
        self.album = track.get("Album", "")
        id = str(track.get("Apple Music Track Identifier", ""))
        if len(id) > 0:
            self.identifiers = {"apple_music_catalog_id": id}
        else:
            self.identifiers = {}
        self.isLibrary = not track.get("Playlist Only Track", False)

class PLPlaylist:

    def __init__(self, caption: str, description: str, rows: [PLTrack]):
        self.caption = caption
        self.description = description
        self.rows = list(rows)

class PLArchive:

    def __init__(self, playlists: [PLPlaylist]):
        self.playlists = list(playlists)

    def archive(self, outfile):
        json.dump(self, outfile, default=encode_data, ensure_ascii=False, indent=4)

def encode_data(data):

    if isinstance(data, PLArchive):
        return {'app_id': "com.obdura.playlistimport", 'app_version': "3.1", 'playlists': data.playlists}

    if isinstance(data, PLPlaylist):
        return {'caption': data.caption, 'description': data.description, 'curator': "", 'rows': data.rows, 'type': "Tracks", 'destination': "Playlist"}

    if isinstance(data, PLTrack):
        return {'name': data.name, 'artist': data.artist, 'album': data.album, 'identifiers': data.identifiers}

    type_name = data.__class__.__name__
    raise TypeError(f"Object of type '{type_name}' is not JSON serializable")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("file", nargs="?",
                        type=argparse.FileType("rb"),
                        default="Apple Media Services information.zip")

    parser.add_argument("--plif_file", nargs="?",
                        type=argparse.FileType("w"),
                        default="Apple Music Library Archive.plif")

    parser.add_argument("--names", nargs="*", default=[])

    args = parser.parse_args()

    with args.file as zip_file:
        download_file = io.BytesIO(zip_file.read())

    with zipfile.ZipFile(download_file) as root:

        content = io.BytesIO(root.read("Apple Media Services information/Apple_Media_Services.zip"))
        ams = zipfile.ZipFile(content)

        zipped = io.BytesIO(ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Library Playlists.json.zip"))
        unzipped = zipfile.ZipFile(zipped)
        with unzipped.open("Apple Music Library Playlists.json", 'r') as json_file:
            am_playlists = json.load(json_file)

        zipped = io.BytesIO(ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Library Tracks.json.zip"))
        unzipped = zipfile.ZipFile(zipped)
        with unzipped.open("Apple Music Library Tracks.json", 'r') as json_file:
            am_tracks = json.load(json_file)

        zipped = io.BytesIO(ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Library Activity.json.zip"))
        unzipped = zipfile.ZipFile(zipped)
        with unzipped.open("Apple Music Library Activity.json", 'r') as json_file:
            am_actions = json.load(json_file)

        likes = ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Likes and Dislikes.csv").decode()
        csv_input = csv.reader(io.StringIO(likes, newline=''), delimiter=',')
        likes_dislikes = list(csv_input)

# Create a dictionary of tracks which we can later use to find Apple Music catalogId's for playlist entries
    track_lookup = {}
    for am_track in am_tracks:
        id = am_track.get('Track Identifier', -1)
        if id == -1:
            continue
        entry = PLTrack(am_track)
        track_lookup[id] = entry

# Create a list of playlists we can see have been deleted at some point so can ignore
    deleted_playlists = []
    deleted_tracks = []
    for action in am_actions:
        if action.get('Transaction Type', "") == "deleteContainer":
            id = action.get('Playlist Identifier', -1)
            if id == -1:
                continue
            deleted_playlists.append(id)
        if action.get('Transaction Type', "") == "deleteItems":
            ids = action.get('Track Identifiers', -1)
            if ids == -1:
                continue
            deleted_tracks += ids

# Create a list of playlists with all of the necessary data to create a PLIF file
    latest_tracks = {}
    for am_playlist in am_playlists:
        
        if am_playlist.get('Container Type',"") != "Playlist":
            continue
            
        id = am_playlist.get('Container Identifier',-1)
        if id == -1:
            continue
            
        if deleted_playlists.count(id) > 0:
            continue
            
        caption = am_playlist.get('Title', "")
        if len(caption) == 0:
            continue

        if len(args.names) > 0:
            if caption not in args.names:
                continue

        description = am_playlist.get('Description',"")
        
        ids = am_playlist.get('Playlist Item Identifiers',[])
        am_playlist_tracks = []
        for id in ids:
            am_track = track_lookup[id]
            am_playlist_tracks.append(am_track)

        if len(am_playlist_tracks) == 0:
            continue

        playlist = PLPlaylist(caption, description, am_playlist_tracks)
        latest_tracks[caption] = playlist

# Next process likes & dislikes:
    likes = []
    dislikes = []
    for row in likes_dislikes:
        track = {}
        desc = row[0].split(" - ")
        if not len(desc) == 2:
            continue
        track["Title"] = desc[1]
        track["Artist"] = desc[0]
        track["Apple Music Track Identifier"] = row[4]

        if row[1] == 'LOVE':
            likes.append(PLTrack(track))
        elif row[1] == 'DISLIKE':
            dislikes.append(PLTrack(track))

    caption = "Apple Music Loved Tracks"
    if caption in args.names:
        playlist = PLPlaylist(caption, "Tracks you've loved in Apple Music", likes)
        latest_tracks[caption] = playlist

    caption = "Apple Music Disliked Tracks"
    if caption in args.names:
        playlist = PLPlaylist(caption, "Tracks you've disliked in Apple Music", dislikes)
        latest_tracks[caption] = playlist

# Finally, library tracks:
    caption = "Apple Music Library Tracks"
    if caption in args.names:
        library = []
        dont_add = set(deleted_tracks)
        for id, track in track_lookup.items():
            if not track.isLibrary:
                continue
            if id in dont_add:
                continue
            library.append(track)
        if len(library) > 0:
            playlist = PLPlaylist(caption, "Tracks you added to your Apple Music library", library)
            latest_tracks[caption] = playlist


# Finally serialise our playlists using a JSON encoder
    playlists = list(latest_tracks.values())
    container = PLArchive(playlists)
    with args.plif_file as plif_file:
        container.archive(plif_file)

    print(f"{len(playlists)} playlist(s) were recovered")
