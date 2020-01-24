import appdaemon.plugins.hass.hassapi as hass
import time
import datetime
import globals
import sys
from queue import Queue
from threading import Thread
import re
"""
    Class Alexa Manager handles sending text to speech messages to Alexa media players
    Following features are implemented:
    - Speak text to choosen media_player
    - Full queue support to manage async multiple TTS commands
    - Full wait to tts to finish to be able to supply a callback method
"""

__NOTIFY__ = "notify/"
SUB_STRING = {"/h": " all'ora","$": "dollaro ", "€": "euro ","°C": " gradi","%": " per cento"}
SUB_ALEXA = [("[\s_]+", " "),("[?!;:,]+", ", "),("\.+", ". "),("[\n\*]", "")]

class Alexa_Manager(hass.Hass):

    def initialize(self) -> None:
        # self.depends_on_module(globals)
        self.wait_time = globals.get_arg(self.args, "wait_time")
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()
        self.version = self.get_ad_version()
        self.log(f"Versione AppDaemon: {self.version}")

    def speak(self, data, alexa_notifier: str):
        """ SPEAK THE PROVIDED TEXT THROUGH THE MEDIA PLAYER """
        default_restore_volume = float(self.get_state(globals.get_arg(self.args, "default_restore_volume")))/100
        wait_time = float(self.get_state(self.wait_time))
        if self.queue.qsize() == 0:
            self.volume_get(data["media_player_alexa"],default_restore_volume)
        message = data["message_tts"]
        
        """ Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done """
        self.queue.put({"title": data["title"], "text": message, "volume": data["volume"], "alexa_player": data["media_player_alexa"], 
                        "alexa_type": data["alexa_type"], "wait_time": wait_time, "alexa_method": data["alexa_method"], "alexa_notifier": alexa_notifier})

    def volume_get(self, media_player, volume: float):
        self.dict_volumes = {}
        restore_volume = volume
        if 'group' in media_player:
            list_player = self.get_state(media_player, attribute="entity_id")
            # self.log(f"MEDIA PLAYER GROUP= {list_player}")
        else:
            list_player = self.converti(media_player)
            # self.log(f"MEDIA PLAYER SINGLE: {list_player}")
        for i in list_player:
            self.dict_volumes[i] = self.get_state(i, attribute="volume_level", default=restore_volume) if self.version >= '4.0.0' else restore_volume
        # self.log(f"GET VOLUMES: {self.dict_volumes}")
        return self.dict_volumes

    def volume_set(self, media_player, volume: float):
        if 'group' in media_player:
            list_player = self.get_state(media_player, attribute="entity_id")
            # self.log(f"SET GRUPPO MEDIA_PLAYER/VOLUME: {list_player} / {volume}")
            self.call_service("media_player/volume_set", entity_id = list_player, volume_level = volume)
        else:
            # self.log(f"SET MEDIA_PLAYER/VOLUME: {media_player} / {volume}")
            self.call_service("media_player/volume_set", entity_id = media_player, volume_level = volume)

    def replace(self, string, substitutions):
        substrings = sorted(substitutions, key=len, reverse=True)
        regex = re.compile('|'.join(map(re.escape, substrings)))
        return regex.sub(lambda match: substitutions[match.group(0)], string)

    def when_tts_done_do(self, callback:callable)->None:
        """ CALLBACK WHEN THE QUEUE OF TTS MESSAGES ARE DONE """
        self._when_tts_done_callback_queue.put(callback)

    def converti(self, stringa): 
        li = list(stringa.replace(" ", "").split(","))
        if len(li) > 1:
            # self.log("SET DUMMY GROUP ALEXA")
            self.set_state("group.hub_media_player_alexa", state = "on", attributes = {"entity_id": li})
        return li

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                alexa_player = data["alexa_player"]

                """ ALEXA TYPE-METHOD """
                if data["alexa_type"] != "push":
                    if data["alexa_type"] == "tts":
                        alexa_data = {"type": "tts"}
                        data["wait_time"] += 2
                    else:
                        data["wait_time"] += 3.5
                        alexa_data = {"type": data["alexa_type"],
                                        "method": data["alexa_method"]
                                        }
                    if self.entity_exists("group.hub_media_player_alexa") and len(self.converti(data["alexa_player"])) > 1:
                        alexa_player = "group.hub_media_player_alexa"

                    """ REPLACE """
                    message_clean = self.replace(data["text"], SUB_STRING)
                    for old, new in SUB_ALEXA:
                        message_clean = re.sub(old, new, message_clean)
                    # self.log(f"PRIMA: {data['text']}")
                    # self.log(f"RISULTATO: {message_clean}")

                    """ SPEECH TIME CALCULATOR """
                    period = message_clean.count(', ') + message_clean.count('. ') ##+ message_clean.count(' - ')
                    words = len(message_clean.split())
                    chars = message_clean.count('')
                    
                    """ ESTIMATED TIME """
                    if (chars/words) > 7 and chars > 90:
                        data["wait_time"] += 7
                        # self.log(f"ADD EXTRA TIME: {data["wait_time"]}"), level="WARNING")
                    # duration = ((chars * 0.00133) * 60) + data["wait_time"] #+ (period/2)
                    # duration1 = (len(message_clean.split()) / 2) + data["wait_time"]
                    # duration2 = ((len(message_clean.split()) / 130) * 60) + data["wait_time"]
                    duration3 = ((words * 0.007) * 60) + data["wait_time"] #+ (period*0.2)
                    # self.log(f"\n| DURATION     | PERIODO = {period} | PAROLE = {words} | CHARS = {chars} \n| \
                    #     (Char*0.00133) = {round(duration,2)} \n| (OLD) = {round(duration1,2)} \n| \
                    #     (char/130) = {round(duration2,2)} \n| (Parole*0.007) = {round(duration3,2)}")

                    """ SPEAK """
                    self.call_service(__NOTIFY__ + data["alexa_notifier"], data = alexa_data, target = alexa_player, message = message_clean)
                    self.volume_set(alexa_player, data["volume"])

                    """ SLEEP AND WAIT FOR THE TTS TO FINISH """
                    time.sleep(duration3)
            except:
                self.log("Errore nel ciclo principale", level="ERROR")
                self.log(sys.exc_info()) 

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting")
                """ RESTORE VOLUME """
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        self.log(f"VOLUME RIPROGRAMMATO: {j} - {i}")
                        # Force Set state
                        self.set_state(i, state = "", attributes = {"volume_level": j})
                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("Errore nel CallBack", level="ERROR")
                    self.log(sys.exc_info()) 
                    pass # Nothing in queue
