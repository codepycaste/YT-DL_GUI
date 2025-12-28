
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QFileDialog, QLabel
from PySide6.QtCore import Slot, Signal, QTimer, QByteArray, QBuffer, QThreadPool, QRunnable, QObject
from PySide6.QtGui import QMovie, QPixmap
import yt_dlp # move to seperate file
import requests

class Worker(QRunnable):
    """
    worker thread
    """
    def __init__(self,ydl_ops,dl_url):
        super().__init__()
        self.ydl_ops = ydl_ops
        self.dl_url = dl_url
        self.format_dict = {"mp3 audio" : "140"} # our dict of desired formats for download -> WHEN SELECTING FORMAT FROM DROPDOWN, TAKES THE VALUE FROM HERE FOR DLP
        self.signals = WorkerSignals()

    @Slot()
    def run(self): #rename? definitely needs traceback/error handling need to get thumbnail from here also
        """
        runs yt_dlp here in seperate thread
        
        """
     
        with yt_dlp.YoutubeDL(self.ydl_ops) as ydl:
            info = ydl.extract_info(self.dl_url, download=False)
            formats = info.get("formats", "formats not found") # -> secondary arg is default return value for get method, implement error checking!
            thumbnail = info.get("thumbnail","OOPS: no thumbnail found")
            accepted_quals = ["mp3 audio"] 
        for data in formats:
            format = data.get("format") 
            size = data.get("filesize", None)
            qual = format[format.index("-")+2:]
            ID = format[:format.index("-")-1]
            ext = data.get("ext", "warning: no ext found")
            #print("ext:",ext)
            #print("ID",ID) # -> this goes to a dictionary and use it to select format for dlp, don't need to show users 
            if size is not None and ext == "mp4": 
                self.format_dict[f"{qual} ~ {"{:.2f}".format(size/1000000)}MB"] = ID 
                accepted_quals.append(f"{qual} ~ {"{:.2f}".format(size/1000000)}MB") 
            #size doesn't quite match actual download
        self.signals.qualities.emit(accepted_quals)
        self.signals.formats.emit(self.format_dict)
        self.signals.thumbnail.emit(thumbnail)
        

class WorkerSignals(QObject):
    """
    callback/traceback signals from running  worker thread
    """
    qualities = Signal(tuple) 
    formats = Signal(dict) 
    thumbnail = Signal(str) 

class MainWindow(QMainWindow):
    """
    Main Window GUI 
    """
    #TODO: need prompts if video already dl. exceptions/error handling
    def __init__(self) -> None: #probably set 'global' object properties like urllink here so can access via slots. 
        
        super().__init__()
        self.setWindowTitle("Lightweight YT Downloader V. 0.01")
        #self.setWindowIcon() TODO: choose a cool icon
        self.dl_url = None #TODO: save last link here
        self.dl_folder = "C:" # TODO: set using method to find default download folder on user system  
        self.format_dict = {} #temp dict while wait for one from ydlp worker
        self.init_UI()
        self.ydl_ops = {
            "format" : "bestvideo+bestaudio/best", 
            "merge_output_format" : "mp4", 
            "outtmpl" : f"{self.dl_folder}/%(title)s", 
            "noplaylist" : True, # just download single vids as of now
            #"listformats" : True, #lists available formats to stdout: -> TS/DB only
            #"list_thumbnails" : True, #lists video thumbnails as image links -> TS/DB only
            #"cookiesfrombrowser" : ("firefox", "default?path to cookies.txt?, None, "YouTUbe"), #not neeeded yet   
            #progress hooks: for download bar info?
        } 
        self.threadpool = QThreadPool()


    def init_UI(self): 
        layout = QVBoxLayout()
        central = QWidget()
        central.setLayout(layout)
        self.link_input = QLineEdit(placeholderText="Paste your Link Here: ") #TODO: input mask/set validator
        self.timer = QTimer() #this all makes sure that the link shows up in the box before dlp does anything/maybe don't need now have multithreading
        self.timer.setSingleShot(True)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.get_link)
        self.link_input.textChanged.connect(lambda: self.timer.start())
        self.link_input.textChanged.connect(self.start_loading)     

          
        startdl_button = QPushButton(text = "Start Download")
        startdl_button.clicked.connect(self.download_button) 
        layout.addWidget(self.link_input)

        #show screenshot/preview/thumbnail w. loading wheel
        self.thumbnail_view = QLabel(text="Video Thumbnail")
        self.thumbnail_view.setMargin(20)
        #loading wheel
        wheel = open(r"Loading_icon.gif", "rb") #need a gif in here
        ba = wheel.read()
        self.buffer = QBuffer()
        self.buffer.setData(ba)
        self.loading = QMovie(self.buffer,QByteArray())
        #video_thumbnail
        self.pixmap = QPixmap()
        

        #TODO: download progress bar/completed notification ?from ytdlp: stdout
        #TODO: subtitles selector
        self.quality_pick = QComboBox(placeholderText="Choose Download Quality")
        layout.addWidget(self.quality_pick)
        self.quality_pick.activated.connect(self.select_formats) 

        dl_layout = QHBoxLayout()
        dl_bar = QWidget()
        dl_bar.setLayout(dl_layout) #Can it be more direct? 
        self.dl_path = QLineEdit(placeholderText=f"Files downloaded to: {self.dl_folder}") #TODO: set default/input mask/validator.probably rename
        self.dl_path.textChanged.connect(self.set_dl_path)
        dl_dialogue = QPushButton(text = "Choose a Download Folder") #TODO: set icon
        dl_dialogue.clicked.connect(self.choose_dl_path)
        layout.addWidget(self.thumbnail_view)
        dl_layout.addWidget(self.dl_path)
        dl_layout.addWidget(dl_dialogue)
        layout.addWidget(dl_bar)
        layout.addWidget(startdl_button) #quite like it at the bottom
        layout.addStretch() 
        self.setCentralWidget(central)

    
    def show_thumbnail(self, url):
        # need some resizing for sure this is massive if leave it alone
        request = requests.get(url)
        self.pixmap.loadFromData(request.content)
        self.thumbnail_view.setPixmap(self.pixmap)
             
    #slots: 
    @Slot() 
    def download_button(self) -> None: #TODO: try-except, find the actual function/access point to dlp, maybe just import all?/multi threading>
       with yt_dlp.YoutubeDL(self.ydl_ops) as ydl: #TODO: multithreading, stdout progress
           ydl.download(self.dl_url)

    @Slot()
    def start_loading(self) -> None: #play loading wheel gif
        self.thumbnail_view.setMovie(self.loading) 
        self.loading.start()
        
             

    @Slot()
    def get_link(self) -> None: #TODO: input checking 
        self.dl_url = self.link_input.text()
        worker = Worker(self.ydl_ops,self.dl_url)
        self.threadpool.start(worker)
        worker.signals.qualities.connect(self.add_quals)
        worker.signals.formats.connect(self.add_formats) 
        worker.signals.thumbnail.connect(self.show_thumbnail)

        ##TODO: get audio from here. ID 140 -> gotta add size of 140/look for other lesser audio quality

    def add_quals(self, q):
        self.quality_pick.addItems(q)

    def add_formats(self, fd):
        self.format_dict = fd

    @Slot()
    def set_dl_path(self) -> None: 
        #TODO: input checking
        self.dl_folder = self.dl_path.text()

    @Slot()
    def choose_dl_path(self) -> None: # opens file dialog window for user to choose filepath for saved downloads
        file_dialog = QFileDialog()
        file_dialog.setWindowTitle("Choose a download folder")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QFileDialog.ViewMode.List)

        if file_dialog.exec():
            selected_path = file_dialog.selectedFiles()[0]
            self.dl_folder = selected_path #probably use a setter above? instead of direct here 

    @Slot()
    def select_formats(self): # applies user chosen format(from combobox) to ytdl ops
        #TODO: reformat! 
        choice = self.quality_pick.currentText()
        ID = self.format_dict[choice] 
        if ID == "140":
            self.ydl_ops["format"] = ID
            self.ydl_ops["outtmpl"]["default"] += ".mp3" 
        else: 
            self.ydl_ops["format"] = ID + "+140" 
            self.ydl_ops["merge_output_format"] = "mp4"

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