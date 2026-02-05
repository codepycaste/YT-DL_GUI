
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QFileDialog, QLabel, QSizePolicy
from PySide6.QtCore import Slot, QTimer, QByteArray, QBuffer, Qt, QThreadPool
from PySide6.QtGui import QMovie, QPixmap
import downloads

from os import path
import requests, traceback

class ThumbnailView(QWidget): 
    """
    custom QWidget class to deal with resizing pixmap -> Size not great gotta set geometry to something good
    """
    def __init__(self): 
        super().__init__()
        self.label = QLabel(self)
        self.pixmap = QPixmap()
        #self.setMargin(20) no attr!
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        #self.setGeometry #maybe can fix gif issues
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label.setText("Video thumb.") # doesn't show.
        #self.label.setScaledContents(False) # maybe needed for gif to keep aspect ratio 

    @Slot()
    def start_loading(self) -> None: #play loading wheel gif, not working
        # NOTE: buffer and loading must be properties or..introduces some kind of buffer error and hard crashes program
        # gif seems to have issues loop related to starting before updating also..just looks terrible resized
        wheel = open(path.join(path.dirname(__file__),"./ui/spinner.gif"), "rb") #replace with qtspinner or whatever its called
        ba = wheel.read()
        self.buffer = QBuffer()
        self.buffer.setData(ba)
        self.loading = QMovie(self.buffer,QByteArray())
        self.label.setMovie(self.loading)
        #self.loading.setScaledSize(self.size()) #
        self.loading.start()
        self.update_loading() #has to be here? init. resize but looks shite

    def update_loading(self): #scales gif to size of qlabel while keeping aspectratio
        try:
            print("scaling .gif") #perhaps issue is here
            self.movie_size = self.loading.currentPixmap().size() #error checking. ! attr error if not initialised obv!
            new_size = self.movie_size.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatio)
            self.loading.setScaledSize(new_size)
        except Exception as e:
            print(f"Unexpected error!")
            traceback.print_exc 
            traceback.print_exception #TODO: error handling 
            if hasattr(e, "message"):
                print(e.message)
            else:
                print(e)
        finally:
            print("loading method complete")

    def show_thumbnail(self, url):
        # some gui freeze here 
        request = requests.get(url)
        self.pixmap.loadFromData(request.content) #?
        print(f"showing thumbnail! size - {self.label.size().height()}x{self.label.size().width()}")
        self.update_pixmap()

    def update_pixmap(self): 
        #error: QPixmap::scaled: Pixmap is a null pixmap: must be checked
        print(f"updating pixmap! size - {self.label.size().height()}x{self.label.size().width()}")
        thumbnail = self.pixmap.scaled(
            self.label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
            )
        print(f"setting pixmap! size - {self.label.size().height()}x{self.label.size().width()}")
        self.label.setPixmap(thumbnail)

    @Slot()
    def resizeEvent(self, event): 
        print(f"resize event triggered! size - {self.label.size().height()}x{self.label.size().width()}")
        self.update_loading()
        self.update_pixmap()  

        return super().resizeEvent(event)

class MainWindow(QMainWindow):
    """
    Main Window GUI 
    """
    #TODO: need prompts if video already dl. exceptions/error handling
    def __init__(self) -> None: 
        
        super().__init__()
        self.setWindowTitle("Lightweight YT Downloader V. 0.01")
        #self.setWindowIcon() TODO: choose a cool icon
        self.dl_url = None #TODO: save last link here
        self.dl_folder = downloads.find_dl_path() 
        #TODO: set using method to find default download folder on user system: DOUBLE SLASHESS
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
        #self.threadpool = QThreadPool()


    def init_UI(self): #TODO: have all text resize with window -> down to default minumum ie what it is now!
        layout = QVBoxLayout()
        central = QWidget()
        central.setLayout(layout)

        self.link_input = QLineEdit(placeholderText="Paste your Link Here: ") #TODO: input mask/set validator
        self.link_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.timer = QTimer() #this all makes sure that the link shows up in the box before dlp does anything/maybe don't need now have multithreading
        self.timer.setSingleShot(True)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.get_link)
        #show screenshot/preview/thumbnail w. loading wheel
        self.thumbnail_view = ThumbnailView()
        self.link_input.textChanged.connect(lambda: self.timer.start())
        #self.thumbnail_view.setMargin(20)   #
        #self.thumbnail_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # set all this in custom widget init
        #self.resizeEvent.connect(self.thumbnail_view.resizeEvent) # just plain wrong
        self.link_input.textChanged.connect(self.thumbnail_view.start_loading)     

          
        startdl_button = QPushButton(text = "Start Download")
        startdl_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        startdl_button.clicked.connect(self.download_button) 

        #TODO: download progress bar/completed notification ?from ytdlp: stdout
        #TODO: subtitles selector
        self.quality_pick = QComboBox(placeholderText="Choose Download Quality")
        self.quality_pick.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.quality_pick.activated.connect(self.select_formats) 

        dl_layout = QHBoxLayout()
        dl_bar = QWidget()
        dl_bar.setLayout(dl_layout) #Can it be more direct? 

        self.dl_path = QLineEdit(placeholderText=f"Files downloaded to: {self.dl_folder}") #TODO: set default/input mask/validator.probably rename
        self.dl_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.dl_path.textEdited.connect(self.set_dl_path) #definitely not textchanged...i think infinite loop

        dl_dialogue = QPushButton(text = "Choose a Download Folder") #TODO: set icon
        dl_dialogue.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dl_dialogue.clicked.connect(self.choose_dl_path)

        dl_layout.addWidget(self.dl_path)
        dl_layout.addWidget(dl_dialogue)
        layout.addWidget(self.thumbnail_view)
        layout.addWidget(self.link_input)
        layout.addWidget(self.quality_pick)
        layout.addWidget(dl_bar)
        layout.addWidget(startdl_button) #quite like it at the bottom
        
        layout.addStretch() 

        self.setCentralWidget(central)
  
    #slots: 
    @Slot() 
    def download_button(self) -> None: #TODO: try-except, stdout progress, 
       
       worker = downloads.Worker(downloads.download,self.ydl_ops,self.dl_url) 
       QThreadPool().start(worker)

    @Slot()
    def get_link(self) -> None: #TODO: input checking, rename...extract info? 
        self.dl_url = self.link_input.text()
        worker = downloads.Worker(downloads.info_process, self.ydl_ops,self.dl_url)
        
        worker.signals.result.connect(self.parse_info)

        QThreadPool().start(worker) 

    
    @Slot()
    def parse_info(self, info):

        self.add_quals(info[0])
        self.add_formats(info[1])
        self.thumbnail_view.show_thumbnail(info[2])


    def add_quals(self, q):
        self.quality_pick.addItems(q)

    def add_formats(self, fd):
        self.format_dict = fd

    @Slot()
    def set_dl_path(self) -> None: 
        #TODO: input checking
        print(f"dl path changed to: {self.dl_path}")
        self.dl_folder = self.dl_path.text()

    @Slot()
    def choose_dl_path(self) -> None: # opens file dialog window for user to choose filepath for saved downloads, change default direct?? when opens
        
        file_dialog = QFileDialog()
        file_dialog.setWindowTitle("Choose a download folder")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QFileDialog.ViewMode.List)

        if file_dialog.exec():
            selected_path = file_dialog.selectedFiles()[0]
            self.dl_folder = selected_path #probably use a setter above? instead of direct here
            self.dl_path.setText(f"{self.dl_folder}") #hmm

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