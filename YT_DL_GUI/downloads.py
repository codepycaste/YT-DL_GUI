"""
This module contains all functions/processes needed to make calls to YT_DLP and downloads from the GUI
via worker objects to prevent GUI freeze

"""
from pathlib import Path
from PySide6.QtCore import QRunnable, Signal, Slot, QObject
import yt_dlp
import traceback

class Worker(QRunnable):
    """
    Class to contain Workers for multithreading function calls/processes
    """
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs #perhaps just ops and url
        self.signals = WorkerSignals()

    @Slot()
    def run(self):

        """
        Initialises runner function with passed **kwargs  
        
        """
        try:

            info = self.fn(*self.args, **self.kwargs) #tuple

        except Exception as e:
            print(f"Unexpected error!")
            traceback.print_exc 
            traceback.print_exception #TODO: error handling 
            if hasattr(e, "message"):
                print(e.message)
            else:
                print(e)
        else:
            if info is not None:
                self.signals.result.emit(info) #create function to deal with this
        finally:
            self.signals.finished.emit("End of thread signal")
            

class WorkerSignals(QObject):

    """
    Signals sent from running workers
    
    finished
        

    error
        tuple (exctype, value, traceback.format_exc())

    result
        object data returned from processing, anything

    progress
        tuple (thread_id, progress_value)
    """
    #defaults:
    finished = Signal(str) 
    #error = Signal(tuple)
    result = Signal(object)
    #progress = Signal(tuple)  # progress_value

    
def download(ops: dict, url: str) -> None:

    """
    main download function utilising yt_dlp
    
    :param ops: YTDLP operation parameters
    :type ops: dict
    :param url: video url 
    :type url: str
    """

    yt_dlp.YoutubeDL(ops).download(url)
        

def info_process(ops: dict, url: str) -> None: #possibly a slot - pass info back via signals
        
        """
        Docstring for info_process
        
        :param ops: Description
        :param url: Description
        """
        
        format_dict = {"High Quality Audio" : "140"} #dict to hold available download formats to be sent to gui
 
        with yt_dlp.YoutubeDL(ops) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", "formats not found") # -> secondary arg is default return value for get method, implement error checking!
            thumbnail = info.get("thumbnail","OOPS: no thumbnail found")
            accepted_quals = ["mp3 audio"]
            title = info.get("title") #maybe want to send more info here
        for data in formats:
            format = data.get("format") 
            size = data.get("filesize", None)
            qual = format[format.index("-")+2:]
            ID = format[:format.index("-")-1]
            ext = data.get("ext", "warning: no ext found")

            if size is not None and ext == "mp4": 
                format_dict[f"{qual} ~ {"{:.2f}".format(size/1000000)}MB"] = ID 
                accepted_quals.append(f"{qual} ~ {"{:.2f}".format(size/1000000)}MB") 
            #size doesn't quite match actual download
        
        result = (accepted_quals,format_dict,thumbnail, title)
        return result 
        ##TODO: get audio from here. ID 140 -> gotta add size of 140/look for other lesser audio quality


def find_dl_path():
    """
    determines default download path for user terminal
    """
    return f"{Path.home()}/Downloads"

#REFERENCE YTDLP INFO/OUTPUT

    """
info keys(['id', 
        'title', 
        'formats', 
        'thumbnails', 
        'thumbnail', 
        'description', 
        'channel_id', 
        'channel_url', 
        'duration', 
        'view_count', 
        'average_rating', 
        'age_limit', 
        'webpage_url', 
        'categories', 
        'tags', 
        'playable_in_embed', 
        'live_status', 
        'media_type', 
        'release_timestamp', 
        '_format_sort_fields', 
        'automatic_captions', 
        'subtitles', 
        'comment_count', 
        'chapters', 
        'heatmap', 
        'like_count', 
        'channel', 
        'channel_follower_count', 
        'uploader', 
        'uploader_id', 
        'uploader_url', 
        'upload_date', 
        'timestamp', 
        'availability', 
        'original_url', 
        'webpage_url_basename', 
        'webpage_url_domain', 
        'extractor', 
        'extractor_key', 
        'playlist', 
        'playlist_index', 
        'display_id', 
        'fulltitle', 
        'duration_string', 
        'release_year', 
        'is_live', 
        'was_live', 
        'requested_subtitles', 
        '_has_drm', 
        'epoch', 
        'requested_formats', 
        'format', 
        'format_id', 
        'ext', 
        'protocol', 
        'language', 
        'format_note', 
        'filesize_approx', 
        'tbr', 
        'width', 
        'height', 
        'resolution', 
        'fps', 
        'dynamic_range', 
        'vcodec', 
        'vbr', 
        'stretched_ratio', 
        'aspect_ratio', 
        'acodec',
        'abr', 
        'asr', 
        'audio_channels'])

[info] Available formats for -6YZ3SAJGzE: 
ID  EXT   RESOLUTION FPS CH │  FILESIZE   TBR PROTO │ VCODEC        VBR ACODEC      ABR ASR MORE INFO 
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
sb2 mhtml 48x27        0    │                 mhtml │ images                                storyboard
sb1 mhtml 80x45        1    │                 mhtml │ images                                storyboard
sb0 mhtml 160x90       1    │                 mhtml │ images                                storyboard
139 m4a   audio only      2 │   1.39MiB   49k https │ audio only        mp4a.40.5   49k 22k low, m4a_dash
140 m4a   audio only      2 │   3.67MiB  129k https │ audio only        mp4a.40.2  129k 44k medium, m4a_dash
251 webm  audio only      2 │   3.64MiB  128k https │ audio only        opus       128k 48k medium, webm_dash
91  mp4   256x144     30    │ ~ 5.20MiB  183k m3u8  │ avc1.4D400C       mp4a.40.5
160 mp4   256x144     30    │   3.40MiB  120k https │ avc1.4d400c  120k video only          144p, mp4_dash
93  mp4   640x360     30    │ ~22.32MiB  787k m3u8  │ avc1.4D401E       mp4a.40.2
134 mp4   640x360     30    │  17.08MiB  602k https │ avc1.4d401e  602k video only          360p, mp4_dash
18  mp4   640x360     30  2 │ ≈20.71MiB  730k https │ avc1.42001E       mp4a.40.2       44k 360p
95  mp4   1280x720    30    │ ~68.65MiB 2420k m3u8  │ avc1.64001F       mp4a.40.2
136 mp4   1280x720    30    │  60.65MiB 2139k https │ avc1.64001f 2139k video only          720p, mp4_dash

48x27 - mhtml ~ storyboardvideo@   0k, 0.42016806722689076fps, video only@  0k
80x45 - mhtml ~ storyboardvideo@   0k, 0.5042016806722689fps, video only@  0k
160x90 - mhtml ~ storyboardvideo@   0k, 0.5042016806722689fps, video only@  0k
audio only - m4a ~ low,   48k, m4a_dash containervideo@   0k, mp4a.40.5@ 48k (22050Hz), 1.39MiB
audio only - m4a ~ medium,  129k, m4a_dash containervideo@   0k, mp4a.40.2@129k (44100Hz), 3.67MiB
160x90 - mhtml ~ storyboardvideo@   0k, 0.5042016806722689fps, video only@  0k
160x90 - mhtml ~ storyboardvideo@   0k, 0.5042016806722689fps, video only@  0k
audio only - m4a ~ low,   48k, m4a_dash containervideo@   0k, mp4a.40.5@ 48k (22050Hz), 1.39MiB
audio only - m4a ~ medium,  129k, m4a_dash containervideo@   0k, mp4a.40.2@129k (44100Hz), 3.67MiB
audio only - webm ~ medium,  128k, webm_dash containervideo@   0k, opus @128k (48000Hz), 3.64MiB
160x90 - mhtml ~ storyboardvideo@   0k, 0.5042016806722689fps, video only@  0k
160x90 - mhtml ~ storyboardvideo@   0k, 0.5042016806722689fps, video only@  0k
audio only - m4a ~ low,   48k, m4a_dash containervideo@   0k, mp4a.40.5@ 48k (22050Hz), 1.39MiB
audio only - m4a ~ medium,  129k, m4a_dash containervideo@   0k, mp4a.40.2@129k (44100Hz), 3.67MiB
audio only - webm ~ medium,  128k, webm_dash containervideo@   0k, opus @128k (48000Hz), 3.64MiB
256x144 - mp4 ~  183k, avc1.4D400C, 30.0fps, mp4a.40.5
256x144 - mp4 ~  183k, avc1.4D400C, 30.0fps, mp4a.40.5
256x144 - mp4 ~ 144p,  119k, mp4_dash container, avc1.4d400c@ 119k, 30fps, video only@  0k, 3.40MiB
640x360 - mp4 ~  786k, avc1.4D401E, 30.0fps, mp4a.40.2
640x360 - mp4 ~ 360p,  602k, mp4_dash container, avc1.4d401e@ 602k, 30fps, video only@  0k, 17.08MiB
640x360 - mp4 ~ 360p,  729k, avc1.42001E, 30fps, mp4a.40.2 (44100Hz), ~20.71MiB
640x360 - mp4 ~ 360p,  729k, avc1.42001E, 30fps, mp4a.40.2 (44100Hz), ~20.71MiB
1280x720 - mp4 ~ 2419k, avc1.64001F, 30.0fps, mp4a.40.2
1280x720 - mp4 ~ 720p, 2138k, mp4_dash container, avc1.64001f@2138k, 30fps, video only@  0k, 60.65MiB
1280x720 - mp4 ~ 2419k, avc1.64001F, 30.0fps, mp4a.40.2
1280x720 - mp4 ~ 2419k, avc1.64001F, 30.0fps, mp4a.40.2
1280x720 - mp4 ~ 720p, 2138k, mp4_dash container, avc1.64001f@2138k, 30fps, video only@  0k, 60.65MiB
    """