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
        self.gh_wait_time = self.args["gh_wait_time"]
        self.gh_select_media_player = self.args["gh_select_media_player"]
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def check_mplayer(self, gh_player: list):
        media_p = list(self.get_state("media_player").keys())
        gh = []
        for item in [x.strip(" ") for x in gh_player] :
            if item in media_p or item == "all":
                gh.append(item)
        return gh

    def check_volume(self, gh_volume):
        media_state = self.get_state("media_player")
        gh = []
        for entity, state in media_state.items(): 
            friendly_name = state["attributes"].get("friendly_name") 
            for item in gh_volume:
                if "gruppo" not in str(item).lower() and item == friendly_name:
                    gh.append(entity)
        return gh

    def volume_set(self, gh_player: list, volume: float):
        if gh_player != ["all"]:
            for item in gh_player:
                self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)

    def volume_get(self, media_player:list, volume: float):
        self.dict_volumes = {}
        for i in media_player:
            self.dict_volumes[i] = self.get_state(i, attribute="volume_level", default=volume)
        return self.dict_volumes

    def replace_regular(self, text: str, substitutions: list):
        for old,new in substitutions:
            text = re.sub(old, new, str(text).strip())
        return text

    def replace_language(self, s: str):
        return (s[:2])

    def speak(self, google, gh_mode: bool, gh_notifier: str):
        """Speak the provided text through the media player"""
        gh_player = self.check_mplayer(self.split_device_list(google["media_player"]))
        gh_volume = self.check_volume(self.get_state(self.gh_select_media_player, attribute="options"))
        self.volume_get(gh_volume,float(self.get_state(self.args["gh_restore_volume"]))/100)
        wait_time = float(self.get_state(self.gh_wait_time))
        message = self.replace_regular(google["message_tts"], SUB_TTS)
        ### set volume
        self.volume_set(gh_player,google["volume"])
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        if google["media_content_id"] != "":
            try:
                self.call_service("media_extractor/play_media", entity_id = gh_player, media_content_id= google["media_content_id"], 
                                media_content_type = google["media_content_type"]) 
            except Exception as ex:
                self.log("An error occurred in GH Manager - Errore in media_content: {}".format(ex),level="ERROR")
                self.log(sys.exc_info())
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
                gh_player = self.check_mplayer(self.split_device_list(data["gh_player"]))
                ### SPEAK
                if data["gh_mode"] == 'on':
                    self.call_service(__NOTIFY__ + data["gh_notifier"], message = data["text"])
                else:
                    if len(gh_player) == 1:
                        entity = gh_player[0]
                    else:
                        entity = gh_player
                    self.call_service(__TTS__ + data["gh_notifier"], entity_id = entity, message = data["text"], language = data["language"])
                    if type(entity) is list:
                        duration = float(len(data["text"].split())) / 3 + data["wait_time"]
                    else:
                        if entity == "all":
                            duration = float(len(data["text"].split())) / 3 + data["wait_time"]
                        elif self.get_state(entity, attribute='media_duration') is None:
                            duration = float(len(data["text"].split())) / 3 + data["wait_time"]
                        else: 
                            duration = self.get_state(entity, attribute='media_duration')
                    #Sleep and wait for the tts to finish
                    time.sleep(duration)
            except Exception as ex:
                self.log("An error occurred in GH Manager - Errore nel Worker: {}".format(ex),level="ERROR")
                self.log(sys.exc_info())

            self.queue.task_done()

            if self.queue.qsize() == 0:
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
