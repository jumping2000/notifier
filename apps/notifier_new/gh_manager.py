import appdaemon.plugins.hass.hassapi as hass
import time
import datetime
import globals
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
__WAIT_TIME__ = 1  # seconds
__TTS_GH__ = "tts/google_translate_say"

class GH_Manager(hass.Hass):

    def initialize(self)->None:
        self.gh_tts = "google_assistant"
        #self.dict_volumes = {}
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def volume_set(self, gh_player: list, volume: float):
        for item in gh_player:
            if self.get_state(item) == "off":
                self.call_service("media_player/turn_on", entity_id = item)  ### Set to the desired volume
            self.log("SET MEDIA_PLAYER/VOLUME: {} / {}".format(item,volume))
            self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)

    def speak(self, data, gh_tts_mode: bool):
        """Speak the provided text through the media player"""
        self.dict_volumes = {}
        gh_player = self.converti(data["media_player_google"])
        for i in gh_player:
            self.dict_volumes[i] = float(self.get_state(globals.get_arg(self.args, "gh_restore_volume")))/100
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ")
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        self.queue.put({"type": "tts", "text": message, "volume": data["volume"], "language": data["language"],
                        "gh_player": data["media_player_google"], "gh_tts_mode": gh_tts_mode })
    
    def when_tts_done_do(self, callback:callable)->None:
        """Callback when the queue of tts messages are done"""
        self._when_tts_done_callback_queue.put(callback)

    def converti(self, stringa)->list: 
        return list(stringa.replace(" ", "").split(","))

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                gh_player = self.converti(data["gh_player"])
                ### set volume
                self.volume_set(gh_player,data["volume"])
                ### Let's hope GH will get up
                time.sleep(__WAIT_TIME__)
                ### SPEAK
                if data["gh_tts_mode"] == 'on':
                    self.call_service(__NOTIFY__ + self.gh_tts, message = data["text"])
                    duration = (len(data["text"].split()) / 3) + __WAIT_TIME__
                    #Sleep and wait for the tts to finish
                    time.sleep(duration)
                else:
                    for entity in gh_player:
                        self.call_service(__TTS_GH__, entity_id = entity, message = data["text"], language = data["language"])
                        time.sleep(__WAIT_TIME__)
                        duration = self.get_state(entity, attribute='media_duration')
                        if not duration:
                            #The TTS already played, set a small duration
                            duration = (len(data["text"].split()) / 3) + __WAIT_TIME__
                            self.log("DURATION-WAIT {}:".format(duration))
                        #Sleep and wait for the tts to finish
                        time.sleep(duration)
            except:
                self.log("Errore nel ciclo principale")
                self.log(sys.exc_info()) 

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting")
                ## RESTORE VOLUME
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        self.log("VOLUME RIPROGRAMMATO: {} - {}".format(j,i))
                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("Errore nel CallBack")
                    self.log(sys.exc_info()) 
                    pass # Nothing in queue

"""
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
                    time.sleep(__WAIT_TIME__)
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