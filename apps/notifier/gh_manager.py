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

    def mediastate_get(self, media_player:list, volume: float):
        self.dict_info_mplayer = {}
        for i in media_player:
            self.dict_info_mplayer[i] = {}
        for i in media_player:
            #self.dict_info_mplayer[i]['volume'] = self.get_state(i, attribute="volume_level", default=volume)
            self.dict_info_mplayer[i]['state'] = self.get_state(i, default='idle')
            self.dict_info_mplayer[i]['media_id'] = self.get_state(i, attribute="media_content_id", default='')
            self.dict_info_mplayer[i]['media_type'] = self.get_state(i, attribute="media_content_type", default='')
            self.dict_info_mplayer[i]['app_name'] = self.get_state(i, attribute="app_name", default='')
            self.dict_info_mplayer[i]['authSig'] = self.get_state(i, attribute="authSig", default='')
        return self.dict_info_mplayer

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
        #self.log("gh_player {}:".format(gh_player))
        self.volume_get(gh_volume,float(self.get_state(self.args["gh_restore_volume"]))/100)
        self.mediastate_get(gh_volume,float(self.get_state(self.args["gh_restore_volume"]))/100)
        #float(self.get_state(globals.get_arg(self.args, "gh_restore_volume")))/100
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
                duration = 0
                gh_player = self.check_mplayer(self.split_device_list(data["gh_player"]))
                ### SPEAK
                if data["gh_mode"].lower()  == 'google assistant':
                    self.call_service(__NOTIFY__ + data["gh_notifier"], message = data["text"])
                else:
                    if len(gh_player) == 1:
                        entity = gh_player[0]
                    else:
                        entity = gh_player
                    self.call_service(__TTS__ + data["gh_notifier"], entity_id = entity, message = data["text"])#, language = data["language"])
                    if (type(entity) is list) or entity == "all" or \
                            (self.get_state(entity, attribute='media_duration') is None) or \
                            float(self.get_state(entity, attribute='media_duration')) > 60 or \
                            float(self.get_state(entity, attribute='media_duration')) == -1:
                        duration = float(len(data["text"].split())) / 2 + data["wait_time"]
                    else:
                        duration = float(self.get_state(entity, attribute='media_duration')) + data["wait_time"]
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
                ## RESTORE MUSIC
                if self.dict_info_mplayer:
                    for k,v in self.dict_info_mplayer.items():
                        temp_media_id = ''
                        temp_media_type = ''
                        temp_app_name = ''
                        temp_auth_sig = ''
                        playing = False
                        for k1,v1 in v.items():
                            if v1 == 'playing':
                                playing = True
                            if k1 == 'media_id':
                                temp_media_id = v1
                            if k1 == 'media_type':
                                temp_media_type = v1
                            if k1 == 'app_name':
                                temp_app_name = v1
                            if k1 == 'authSig':
                                temp_auth_sig = v1
                        self.log("Costruzione del servizio: {} - {} - {} - {} - {}".format(k, temp_media_id, temp_media_type, temp_app_name,temp_auth_sig ))
                        if playing and (temp_auth_sig !=''):
                            self.call_service("media_player/play_media", entity_id = k, media_content_id = temp_media_id, media_content_type = temp_media_type, authSig = temp_auth_sig)
                        elif playing and temp_app_name =='Spotify':
                            self.call_service("spotcast/start", entity_id = k)
                        elif playing:
                            self.call_service("media_player/play_media", entity_id = k, media_content_id = temp_media_id, media_content_type = temp_media_type)
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
