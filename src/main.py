from logging import debug
import os
import sys
import platform
import json
import youtube_dl
from datetime import datetime, timedelta


from api.DbApi import DbApi
from api.YoutubeApi import YoutubeApi
from models.VideoInfo import VideoInfo

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def loadConfigs():
    sys.stdout.write("<<< Loading configs >>>\n")
    with open("conf/env.json") as jsonFile:
        env_json = json.load(jsonFile)
        jsonFile.close()

    with open("conf/scraper.json") as jsonFile:
        scraper_json = json.load(jsonFile)
        jsonFile.close()

    return (env_json, scraper_json)


env_json, scraper_json = loadConfigs()

youtube_scrapers = scraper_json["youtube"]


if youtube_scrapers != None:

    api = YoutubeApi(env_json["youtube-api-key"])

    playlist_ids = [s["channel-id"] for s in youtube_scrapers]

    sys.stdout.write("<<< Loading playlist ids >>>\n")
    upload_ids = api.loadChanelUploadIds(playlist_ids)

    sys.stdout.write("<<< Loading videos >>>\n")
    videosPerChanel = api.loadPlaylistVideoInfo(upload_ids)

    with DbApi(env_json["db-path"]) as db:
        sys.stdout.write("<<< Creating/checking DB >>>\n")
        VideoInfo.createTable(db)

        nameTemplateBase = env_json["music-folder"]
        nameTemplate = "%(title)s.%(ext)s"
        templateLinker = "/"

        # sometimes windows is weird, mess around with these if thats the problem
        if platform.system() == 'Windows':
            nameTemplate = "%(title)s.%(ext)s"
            templateLinker = "/"

        outputTemplate = nameTemplateBase + templateLinker + nameTemplate
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outputTemplate,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:

            for chanel_idx, chanel in enumerate(videosPerChanel):
                now = datetime.now()
                day_amount = youtube_scrapers[chanel_idx].get(
                    "max_age_in_days", 7)
                max_age = timedelta(days=day_amount)
                time_border = now - max_age

                for vid in chanel:
                    sys.stdout.write("\n")
                    sys.stdout.write("<<< Checking " + vid.title + " >>>\n")

                    # break if already loaded
                    existingItems = VideoInfo.getModelByIds(db, [vid.id])
                    exists = len(existingItems) > 0
                    if exists and existingItems[0]["has_been_loaded"]:
                        sys.stdout.write("<<< " +
                                         vid.title + " has been downloaded >>>\n")
                        continue

                    if vid.published_at < time_border:
                        sys.stdout.write("<<< " +
                                         vid.title + " is too old >>>\n")
                        continue

                    videoPath = nameTemplateBase + templateLinker + vid.title + '.mp3'
                    fileExists = os.path.exists(videoPath)

                    if not fileExists:
                        link = "https://www.youtube.com/watch?v={vid_id}".format(
                            vid_id=vid.video_id)
                        sys.stdout.write("<<< Downloading " +
                                         vid.title + " >>>\n")
                        ydl.download([link])
                    else:
                        sys.stdout.write(
                            vid.title + '.mp3' + " already exists on disk, skipping download")

                    # set data, and name according to nameTemplate
                    vid.file_path = videoPath
                    vid.has_been_loaded = 1

                    # insert into DB or update existing one
                    if not exists:
                        VideoInfo.insertModel(db, vid)
                    else:
                        VideoInfo.setModelLoaded(db, vid.id, vid.file_path)
