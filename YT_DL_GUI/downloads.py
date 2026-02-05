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
        
        result = (accepted_quals,format_dict,thumbnail)
        return result 
        ##TODO: get audio from here. ID 140 -> gotta add size of 140/look for other lesser audio quality


def find_dl_path():
    """
    determines default download path for user terminal
    """
    return f"{Path.home()}/Downloads"