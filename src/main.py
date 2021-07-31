from logging import debug
import os
import sys
import platform
import shutil
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


def downloadVideo(vid):
    link = "https://www.youtube.com/watch?v={vid_id}".format(
        vid_id=vid.video_id)
    sys.stdout.write("<<< Downloading " +
                     vid.title + " >>>\n")
    ydl.download([link])


def shouldDownloadVideo(vid, time_border):
    if vid.published_at < time_border:
        sys.stdout.write("<<< " +
                         vid.title + " is too old >>>\n")
        return False
    return True


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

                    videoPath = nameTemplateBase + templateLinker + vid.title + '.mp3'
                    existingItems = VideoInfo.getModelByIds(db, [vid.id])
                    existsInDb = len(existingItems) > 0
                    existsOnDisk = os.path.exists(videoPath)
                    dbItem = existingItems[0] if existsInDb else None
                    existsOnDiskExpectedLocation = existsInDb and os.path.exists(
                        dbItem["file_path"])

                    if existsInDb and not existsOnDisk:
                        # download and update DB if downloading to an new location
                        # otherwise it has been removed externally

                        isSameLocation = videoPath == dbItem["file_path"]

                        if existsOnDiskExpectedLocation and not isSameLocation:
                            try:
                                shutil.copyfile(dbItem["file_path"], videoPath)
                                sys.stdout.write(
                                    vid.title + '.mp3' + " copied to new location\n")

                                vid.file_path = videoPath
                                vid.has_been_loaded = 1
                                VideoInfo.setModelLoaded(
                                    db, vid.id, vid.file_path)
                            except:
                                sys.stdout.write(
                                    vid.title + '.mp3' + " could not be copied\n")

                        elif shouldDownloadVideo(vid, time_border) and not isSameLocation:
                            downloadVideo(vid)

                            vid.file_path = videoPath
                            vid.has_been_loaded = 1
                            VideoInfo.setModelLoaded(db, vid.id, vid.file_path)
                        else:
                            sys.stdout.write(
                                vid.title + '.mp3' + " has been removed/rejected, skipping download\n")

                    elif existsOnDisk and not existsInDb:
                        # update DB
                        vid.file_path = videoPath
                        vid.has_been_loaded = 1
                        VideoInfo.insertModel(db, vid)
                        sys.stdout.write(
                            vid.title + '.mp3' + " missing in DB, updating\n")

                    elif existsOnDisk and existsOnDisk:
                        # warn and do nothing
                        sys.stdout.write(
                            vid.title + '.mp3' + " already exists on disk, skipping download\n")

                    elif not existsOnDisk and not existsInDb:
                        # download to disk and instert into DB
                        if shouldDownloadVideo(vid, time_border):
                            downloadVideo(vid)

                            vid.file_path = videoPath
                            vid.has_been_loaded = 1
                            VideoInfo.insertModel(db, vid)
