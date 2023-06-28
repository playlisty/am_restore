#!/usr/bin/env python3
#
# This is a simple Python script which tries to re-create playlists from an 'Apple Media Services information' archive
#

import json
import zipfile
import io
import argparse
import csv

# Define serialisable Track, Playlist & Archive classes

class PLTrack:

    def __init__(self, track):
        self.name = str(track["Title"])
        self.artist = track.get("Artist", "")
        self.album = track.get("Album", "")
        catalog_id = str(track.get("Apple Music Track Identifier", ""))
        if len(catalog_id) > 0:
            self.identifiers = {"apple_music_catalog_id": catalog_id}
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

    def save(self, outfile):
        json.dump(self, outfile, default=encode_data, ensure_ascii=False, indent=4)

# Serialisation helper function, passed-in to json.dump

def encode_data(data):

    if isinstance(data, PLArchive):
        return {'app_id': "com.obdura.playlistimport", 'app_version': "3.1", 'playlists': data.playlists}

    if isinstance(data, PLPlaylist):
        return {'caption': data.caption, 'description': data.description, 'curator': "", 'rows': data.rows,
                'type': "Tracks", 'destination': "Playlist"}

    if isinstance(data, PLTrack):
        return {'name': data.name, 'artist': data.artist, 'album': data.album, 'identifiers': data.identifiers}

    type_name = data.__class__.__name__
    raise TypeError(f"Object of type '{type_name}' is not JSON serializable")


if __name__ == "__main__":

# Parse command-line arguments. Also opens input file & creates files output file:
    parser = argparse.ArgumentParser()

    parser.add_argument("file", nargs="?",
                        type=argparse.FileType("rb"),
                        default="Apple Media Services information.zip")

    parser.add_argument("--plif_file", nargs="?",
                        type=argparse.FileType("w"),
                        default="Apple Music Library Archive.plif")

    parser.add_argument("--names", nargs="*", default=[])

    args = parser.parse_args()

# Read the input Zip file and extract the 4 files we will need into variables:
    with args.file as zip_file:
        download_file = io.BytesIO(zip_file.read())
        
    # Opens a Zip file within the Zip file:
    with zipfile.ZipFile(download_file) as root:
        content = io.BytesIO(
            root.read("Apple Media Services information/Apple_Media_Services.zip")
        )

    ams = zipfile.ZipFile(content)

    # Read playlists file:
    zipped = io.BytesIO(
        ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Library Playlists.json.zip")
    )
    unzipped = zipfile.ZipFile(zipped)
    with unzipped.open("Apple Music Library Playlists.json", 'r') as json_file:
        am_playlists = json.load(json_file)

    # Read library tracks file:
    zipped = io.BytesIO(
        ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Library Tracks.json.zip")
    )
    unzipped = zipfile.ZipFile(zipped)
    with unzipped.open("Apple Music Library Tracks.json", 'r') as json_file:
        am_tracks = json.load(json_file)

    # Read user actions file:
    zipped = io.BytesIO(
        ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Library Activity.json.zip")
    )
    unzipped = zipfile.ZipFile(zipped)
    with unzipped.open("Apple Music Library Activity.json", 'r') as json_file:
        am_actions = json.load(json_file)

    # Read likes & dislikes playlist file:
    likes = io.StringIO(
        ams.read("Apple_Media_Services/Apple Music Activity/Apple Music Likes and Dislikes.csv").decode(),
        newline=''
    )
    reader = csv.reader(likes, delimiter=',')
    next(reader, None)  # Skip header row
    likes_dislikes = list(reader)

# Create dictionaries of tracks which we can later use to find Apple Music catalogId's for playlist entries
    track_lookup = {}
    for am_track in am_tracks:
        track_id = am_track.get('Track Identifier', -1)
        if track_id == -1:
            continue
        entry = PLTrack(am_track)
        track_lookup[track_id] = entry

# Create lists of playlists & tracks we can see have been deleted at some point so can ignore
    deleted_playlists = []
    deleted_tracks = []
    for action in am_actions:
        if action.get('Transaction Type', "") == "deleteContainer":
            track_id = action.get('Playlist Identifier', -1)
            if track_id == -1:
                continue
            deleted_playlists.append(track_id)
        if action.get('Transaction Type', "") == "deleteItems":
            ids = action.get('Track Identifiers', -1)
            if ids == -1:
                continue
            deleted_tracks += ids

# Create a list of playlists with all the data needed to create a PLIF file
    latest_tracks = {}
    for am_playlist in am_playlists:
        
        if am_playlist.get('Container Type', "") != "Playlist":
            continue
            
        track_id = am_playlist.get('Container Identifier', -1)
        if track_id == -1:
            continue
            
        if deleted_playlists.count(track_id) > 0:
            continue
            
        playlist_name = am_playlist.get('Title', "")
        if len(playlist_name) == 0:
            continue

        if len(args.names) > 0:
            if playlist_name not in args.names:
                continue

        playlist_description = am_playlist.get('Description', "")
        
        ids = am_playlist.get('Playlist Item Identifiers', [])
        am_playlist_tracks = []
        for track_id in ids:
            am_track = track_lookup[track_id]
            am_playlist_tracks.append(am_track)

        if len(am_playlist_tracks) == 0:
            continue

        playlist = PLPlaylist(playlist_name, playlist_description, am_playlist_tracks)
        latest_tracks[playlist_name] = playlist

# Next process likes & dislikes:
    likes = []
    dislikes = []
    for row in likes_dislikes:
        liked_disliked_track = {}
        desc = row[0].split(" - ")
        if len(desc) < 2:
            print(f"Track skipped (incomplete description): {row[0]}")
            continue
        liked_disliked_track["Title"] = desc[1]
        liked_disliked_track["Artist"] = desc[0]
        liked_disliked_track["Apple Music Track Identifier"] = row[4]

        if row[1] == 'LOVE':
            likes.append(PLTrack(liked_disliked_track))
        elif row[1] == 'DISLIKE':
            dislikes.append(PLTrack(liked_disliked_track))

    playlist_name = "Apple Music Loved Tracks"
    if playlist_name in args.names:
        playlist = PLPlaylist(playlist_name, "Tracks you've loved in Apple Music", likes)
        latest_tracks[playlist_name] = playlist

    playlist_name = "Apple Music Disliked Tracks"
    if playlist_name in args.names:
        playlist = PLPlaylist(playlist_name, "Tracks you've disliked in Apple Music", dislikes)
        latest_tracks[playlist_name] = playlist

# Finally, library tracks:
    playlist_name = "Apple Music Library Tracks"
    if playlist_name in args.names:
        library = []
        dont_add = set(deleted_tracks)
        for track_id, liked_disliked_track in track_lookup.items():
            if not liked_disliked_track.isLibrary:
                continue
            if track_id in dont_add:
                continue
            library.append(liked_disliked_track)
        if len(library) > 0:
            playlist = PLPlaylist(playlist_name, "Tracks you added to your Apple Music library", library)
            latest_tracks[playlist_name] = playlist


# Now serialise our playlists into the output file
    final_playlists = list(latest_tracks.values())
    container = PLArchive(final_playlists)
    with args.plif_file as plif_file:
        container.save(plif_file)

    print(f"{len(final_playlists)} playlist(s) were recovered")
