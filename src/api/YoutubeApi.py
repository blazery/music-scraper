import googleapiclient.discovery
from models.VideoInfo import VideoInfo


class YoutubeApi:
    api_service_name = "youtube"
    api_version = "v3"

    def __init__(self, DEVELOPER_KEY):

        self.youtube = googleapiclient.discovery.build(
            YoutubeApi.api_service_name,
            YoutubeApi.api_version,
            developerKey=DEVELOPER_KEY)
        return

    def loadChanelUploadIds(self, channel_ids: list[str]):

        request = self.youtube.channels().list(
            part="contentDetails",
            id=",".join(channel_ids)
        )
        response = request.execute()
        uploadIds = [i["contentDetails"]["relatedPlaylists"]["uploads"]
                     for i in response["items"]]
        return uploadIds

    def loadPlaylistVideoInfo(self, list_ids: list[str]) -> list[list[VideoInfo]]:

        itemsPerPlaylist = []

        for id in list_ids:
            request = self.youtube.playlistItems().list(
                part="snippet",
                maxResults=25,
                playlistId=id
            )
            response = request.execute()

            items = ([VideoInfo({
                "id": i["id"],
                "video_id": i["snippet"]["resourceId"]["videoId"],
                "published_at": i["snippet"]["publishedAt"],
                "title": i["snippet"]["title"]
            }) for i in response['items']])
            itemsPerPlaylist.append(items)

        return itemsPerPlaylist
