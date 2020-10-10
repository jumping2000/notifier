import hassapi as hass
import time
import datetime
import re
import sys
from queue import Queue
from threading import Thread

#from threading import Event

"""
Class TTS Manager handles sending text to speech messages to media players
Following features are implemented:
- Speak text to choosen media_player
- Full queue support to manage async multiple TTS commands
- Full wait to tts to finish to be able to supply a callback method
"""

__NOTIFY__ = "notify/"
__TTS__ = "tts/"
SUB_TTS = [("[\*\-\[\]_\(\)\{\~\|\}\s]+"," ")]

class GH_Manager(hass.Hass):

    def initialize(self)->None:
        #self.gh_wait_time = globals.get_arg(self.args, "gh_wait_time")
        self.gh_wait_time = self.args["gh_wait_time"]

        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def volume_set(self, gh_player: list, volume: float):
        if gh_player != ["all"]:
            for item in gh_player:
                #if self.get_state(item) == "off":
                #    self.call_service("media_player/turn_on", entity_id = item)  ### Set to the desired volume
                #self.log("SET MEDIA_PLAYER/VOLUME: {} / {}".format(item,volume))
                self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)
#        else:
#            for item in self.get_state("media_player").keys():
#                if self.get_state(item) is not "unavailable":
#                    self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)

    def replace_regular(self, text: str, substitutions: list):
        for old,new in substitutions:
            text = re.sub(old, new, str(text).strip())
        return text

    def replace_language(self, s: str):
        return (s[:2])

    def speak(self, google, gh_mode: bool, gh_notifier: str):
        """Speak the provided text through the media player"""
        self.dict_volumes = {}
        gh_player = self.split_device_list(google["media_player"])
        for i in gh_player:
            #self.dict_volumes[i] = float(self.get_state(globals.get_arg(self.args, "gh_restore_volume")))/100
            self.dict_volumes[i] = float(self.get_state(self.args["gh_restore_volume"]))/100
        wait_time = float(self.get_state(self.gh_wait_time))
        message = self.replace_regular(google["message_tts"], SUB_TTS)
        ### set volume
        self.volume_set(gh_player,google["volume"])
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        if google["media_content_id"] != '':
            self.call_service("media_extractor/play_media", entity_id = gh_player, media_content_id= google["media_content_id"], 
                            media_content_type = google["media_content_type"])  
        else:
            self.queue.put({"type": "tts", "text": message, "volume": google["volume"], "language": self.replace_language(google["language"]), 
                    "gh_player": google["media_player"], "wait_time": wait_time, "gh_mode": gh_mode, "gh_notifier": gh_notifier})

    def when_tts_done_do(self, callback:callable)->None:
        """Callback when the queue of tts messages are done"""
        self._when_tts_done_callback_queue.put(callback)

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                gh_player = self.split_device_list(data["gh_player"])
                ### SPEAK
                if data["gh_mode"] == 'on':
                    self.call_service(__NOTIFY__ + data["gh_notifier"], message = data["text"])
                else:
                    for entity in gh_player:
                        self.call_service(__TTS__ + data["gh_notifier"], entity_id = entity, message = data["text"], language = data["language"])
                        time.sleep(data["wait_time"])
                        duration = 1.0
                        if entity == "all":
                            duration = (len(int(data["text"].split())) / 3) + data["wait_time"]
                        else: 
                            duration = self.get_state(entity, attribute='media_duration')
                        #Sleep and wait for the tts to finish
                        time.sleep(duration)
            except Exception as ex:
                self.log("An error occurred in GH Manager - Errore nel Worker: {}".format(ex),level="ERROR")
                self.log(sys.exc_info())

            self.queue.task_done()

            if self.queue.qsize() == 0:
                #self.log("QSIZE = 0 - Worker thread exiting")
                ## RESTORE VOLUME
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        # Force Set state
                        self.set_state(i, state="", attributes = {"volume_level": j})
                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("An error occurred in GH Manager - Errore nel CallBack", level="ERROR")
                    self.log(sys.exc_info()) 
                    pass # Nothing in queue


"""
self.log("[GH NOTIFICA]: {} - {} - {}".format(data["gh_mode"], data["gh_notifier"], data["text"]))
                        #self.log("VOLUME RIPROGRAMMATO: {} - {}".format(j,i))
                try:
                    self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)
                except Exception as ex:
                    self.log("An error occurred in GH Manager - Errore in VolumeSet: {}".format(ex),level="ERROR")
                    self.log(sys.exc_info())
                    pass
        #self.log("MESSAGE TTS: {}".format(message))
                ### Let's hope GH will get up
                #time.sleep(data["wait_time"])
#self.log("DURATION-WAIT {}:".format(duration))
#    def converti(self, stringa)->list: 
#        return list(stringa.replace(" ", "").split(","))
SPEECH TIME CALCULATOR 
#                period = data["text"].count(', ') + data["text"].count('. ')
#                words = len(data["text"].split())
                #chars = data["text"].count('')
                    #duration = ((words * 0.008) * 60) + data["wait_time"] + (period*0.2)
                    # duration = (len(data["text"].split()) / 3) + data["wait_time"]
                    #Sleep and wait for the tts to finish
                    #time.sleep(duration)

    def retry(exceptions, tries=4, delay=3, backoff=2, logger=None):
        
        Retry calling the decorated function using an exponential backoff.
        Args:
        exceptions: The exception to check. may be a tuple of exceptions to check.
        tries: Number of times to try (not retry) before giving up.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier (e.g. value of 2 will double the delay each retry).
        logger: Logger to use. If None, print.
        
        def deco_retry(f):
            @wraps(f)
            def f_retry(*args, **kwargs):
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return f(*args, **kwargs)
                    except exceptions as e:
                        msg = '{}, Retrying in {} seconds...'.format(e, mdelay)
                        if logger:
                            logger.warning(msg)
                        else:
                            self.log("retry decorator: {} ".format(msg))
                        time.sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                return f(*args, **kwargs)
            return f_retry  # true decorator
        return deco_retry

    def volume_get(self, entity):
        Retrieve the audio player"s volume.
        self.log("STATO MEDIA_PLAYER: {}".format(self.get_state(entity)))
        if self.get_state(entity) == "off":
            self.log("accendo il media player: {}".format(entity))
            self.call_service("media_player/turn_on", entity_id = entity)
        return round(float(self.get_state(entity = entity, attribute="volume_level") or 0.24),2)

    def volume_callback(self, kwargs):
        for item in self.get_state(globals.get_arg(self.args, "gh_mplayer"), attribute="all")["attributes"]["entity_id"]:
            try:
                if self.get_state(item) == "off":
                    self.call_service("media_player/turn_on", entity_id = item)
                    time.sleep(wait_time)
                self.dict_volumes[item] = round(float(self.get_state(entity = item, attribute="volume_level") or 0.3),2)
            except:
                self.log ("Errore nel salvataggio volumi")
        self.log("DICT SALVA VOLUMI: {} ".format(self.dict_volumes))

    def terminate(self):
        self.cancel_timer(self.handle_mplayer)

    def volume_save(self, volume_level)->dict:
        dict_volumes = {}
        for item in self.get_state(globals.get_arg(self.args, "gh_mplayer"), attribute="all")["attributes"]["entity_id"]:
            dict_volumes[item] = volume_level
        self.log("DICT SALVA VOLUMI: {} ".format(dict_volumes))
        return dict_volumes

"""