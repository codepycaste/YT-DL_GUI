
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QFileDialog, QLabel, QSizePolicy
from PySide6.QtCore import Slot, QTimer, QByteArray, QBuffer, Qt, QThreadPool, QSize, QRect
from PySide6.QtGui import QMovie, QPixmap, QPainter
import downloads

from os import path
import requests, traceback

class ThumbnailView(QLabel): 
    """
    custom QWidget class to deal with resizing pixmap -> Size not great gotta set geometry to something good
    guess we're gonna use the guide on stackexchange. 
    -> https://stackoverflow.com/questions/77602181/pyside6-how-do-i-resize-a-qlabel-playing-a-qmovie-and-maintain-the-movies-orig
    """
    def __init__(self, *args, **kwargs): #maybe need some simple flags to determine what to show.
        super().__init__(*args, **kwargs)
        self._movieSize = QSize()
        self._minSize = QSize()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buffer = None
        self.ba = None
        self._pixmap = QPixmap()

    def minimumSizeHint(self):
        if self._minSize.isValid():
            return self._minSize
        return super().minimumSizeHint()
    
    def setMovie(self, movie):

        if self.movie() == movie:
            return
        super().setMovie(movie)

        if not isinstance(movie, QMovie) or not movie.isValid():
            self._movieSize = QSize()
            self._minSize = QSize()
            self.updateGeometry()
            return

        cf = movie.currentFrameNumber()
        state = movie.state()
        movie.jumpToFrame(0)
        count = movie.frameCount() if movie.frameCount() > 0 else 1
        rect = QRect()
        for _ in range(count):
            movie.jumpToNextFrame()
            rect |= movie.frameRect()

        width = rect.x() + rect.width()
        height = rect.y() + rect.height()

        if width > 0 and height > 0:
            self._movieSize = QSize(width, height)
        else: 
            pm = movie.currentPixmap()
            self._movieSize = pm.size()

        minimum = min(self._movieSize.width(), self._movieSize.height()) if self._movieSize.isValid() else 0
        if minimum <= 0:
            self._minSize = QSize()
        else:
            base = min(4, minimum)
            maximum = max(self._movieSize.width(), self._movieSize.height())
            ratio = maximum/minimum if minimum else 1
            self._minSize = QSize(base, round(base * ratio))
            if self._movieSize.width() == minimum:
                self._minSize.transpose()

        movie.jumpToFrame(cf)
        if state == movie.MovieState.Running:  
            movie.setPaused(False)
        self.updateGeometry()

    def paintEvent(self, event):
        movie = self.movie()
        if not isinstance(movie, QMovie) or not movie.isValid():
            super().paintEvent(event)
            return

        qp = QPainter(self)

        try:
            self.drawFrame(qp)
        except Exception:
            print("Exception encountered during paintEvent")

        cr = self.contentsRect()
        margin = self.margin()
        cr.adjust(margin, margin, -margin, -margin)

        style = self.style()
        alignment = style.visualAlignment(self.layoutDirection(), self.alignment())
        maybeSize = self._movieSize.scaled(cr.size(), Qt.AspectRatioMode.KeepAspectRatio)

        if maybeSize != movie.scaledSize():
            movie.setScaledSize(maybeSize)
            style.drawItemPixmap(
                qp, cr, alignment, movie.currentPixmap().scaled(cr.size(), Qt.AspectRatioMode.KeepAspectRatio)
            )

        else:
            style.drawItemPixmap(
                qp, cr, alignment, movie.currentPixmap()
            )

    @Slot()
    def start_loading(self) -> None: 
        # NOTE: buffer and loading must be properties or..introduces some kind of buffer error and hard crashes program
        # wanted to replace with the pyqtspinner but it hasn't been playing well with pyside

        if not self.buffer and not self.ba: 
            gif = path.join(path.dirname(__file__),"ui\\spinner.gif")
            wheel = open(gif, "rb") 
            self.ba = wheel.read()
            self.buffer = QBuffer()
            self.buffer.setData(self.ba)
            self.loading = QMovie(self.buffer,QByteArray())
            self.buffer.close() #!!
            self.setMovie(self.loading)
        
            self.loading.start() #must be here!

        else:
            self.setMovie(self.loading)
            self.loading.start()

    @Slot()
    def show_thumbnail(self, url):
        request = requests.get(url)
        self._pixmap.loadFromData(request.content) 
        self.setPixmap(self._pixmap)
        self.update_pixmap()
    
    @Slot()
    def clear_pixmap(self):
        if self._pixmap.isNull():
            return
        else:
            self._pixmap = QPixmap()
            self.setPixmap(self._pixmap)

    def update_pixmap(self): 
        thumbnail = self._pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
            )
        self.setPixmap(thumbnail)

    @Slot()
    def resizeEvent(self, event): 
        if self._pixmap.isNull():
            return
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
        #thumbnail is  a bit small upper and lower layouts needed
        upper = QWidget()
        lower = QWidget()
        upper_layout = QHBoxLayout()
        lower_layout = QVBoxLayout()
        upper.setLayout(upper_layout)
        lower.setLayout(lower_layout)

        self.link_input = QLineEdit(placeholderText="Paste your Link Here: ") #TODO: input mask/set validator
        self.link_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.timer = QTimer() #this all makes sure that the link shows up in the box before dlp does anything
        self.timer.setSingleShot(True)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.get_link)
        #show screenshot/preview/thumbnail w. loading wheel
        self.thumbnail_view = ThumbnailView()
        self.link_input.textChanged.connect(lambda: self.timer.start())
        #self.thumbnail_view.setMargin(20)   #
        self.link_input.textChanged.connect(self.thumbnail_view.start_loading)     

          
        startdl_button = QPushButton()
        startdl_button.setText("Start Download")
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
        self.dl_path.textEdited.connect(self.set_dl_path) #definitely not textchanged..think infinite loop

        dl_dialogue = QPushButton()
        dl_dialogue.setText("Choose a Download Folder") #TODO: set icon
        dl_dialogue.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dl_dialogue.clicked.connect(self.choose_dl_path)

        dl_layout.addWidget(self.dl_path)
        dl_layout.addWidget(dl_dialogue)
        
        upper_layout.addWidget(self.thumbnail_view)
        #vid info and progress bar/stdout go in this upper portion
        info_pain = QWidget()
        info_layout = QVBoxLayout()
        self.title_bar = QLabel(text = "Video Title")
        info_layout.addWidget(self.title_bar)
        info_pain.setLayout(info_layout)
        

        upper_layout.addWidget(info_pain)

        lower_layout.addWidget(self.link_input)
        lower_layout.addWidget(self.quality_pick)
        lower_layout.addWidget(dl_bar)
        lower_layout.addWidget(startdl_button) #quite like it at the bottom
        
        layout.addWidget(upper)
        layout.addWidget(lower)
        #layout.addStretch() 

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
        self.get_title(info[3])

    def add_quals(self, q):
        self.quality_pick.addItems(q)

    def add_formats(self, fd):
        self.format_dict = fd

    def get_title(self, title):
        self.title_bar.setText(title)

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
