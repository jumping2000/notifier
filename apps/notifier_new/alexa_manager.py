import appdaemon.plugins.hass.hassapi as hass
import time
import datetime
import globals
import sys
from queue import Queue
from threading import Thread

"""
Class Alexa Manager handles sending text to speech messages to Alexa media players
Following features are implemented:
- Speak text to choosen media_player
- Full queue support to manage async multiple TTS commands
- Full wait to tts to finish to be able to supply a callback method
"""

__NOTIFY__ = "notify/"
__WAIT_TIME__ = 1  # seconds

class Alexa_Manager(hass.Hass):

    def initialize(self) -> None:
        self.alexa_tts = "alexa_media"
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def speak(self, data):
        """ Speak the provided text through the media player """
        default_restore_volume = float(self.get_state(globals.get_arg(self.args, "default_restore_volume")))/100
        if self.queue.qsize() == 0:
            self.volume_get(data["media_player_alexa"],default_restore_volume)
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ").replace("_"," ").replace("!",".")
        """ Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done """
        self.queue.put({"type": "tts", "text": message, "volume": data["volume"],
                        "alexa_player": data["media_player_alexa"], "alexa_type": data["alexa_type"], "alexa_method": data["alexa_method"] })

    def volume_get(self, media_player, volume: float):
        self.dict_volumes = {}
        restore_volume = volume
        if 'group' in media_player:
            list_player = self.get_state(media_player, attribute="entity_id")
            self.log("ALEXA GROUP= {}".format(list_player))
        else:
            list_player = self.converti(media_player)
            self.log("ALEXA SINGLE: {}".format(list_player))
        for i in list_player:
            self.dict_volumes[i] = self.get_state(entity = i, attribute="volume_level") or restore_volume
            self.log("GET ALEXA VOLUMES: {} - {}".format(i,self.dict_volumes[i]))
        return self.dict_volumes

    def volume_set(self, alexa_player, volume: float):
        if 'group' in alexa_player:
            entity = self.get_state(alexa_player, attribute="entity_id")
            self.log("SET GRUPPO MEDIA_PLAYER/VOLUME: {} / {}".format(entity,volume))
            self.call_service("media_player/volume_set", entity_id = entity, volume_level = volume)
        else:
            self.log("SET MEDIA_PLAYER/VOLUME: {} / {}".format(alexa_player,volume))
            self.call_service("media_player/volume_set", entity_id = alexa_player, volume_level = volume)

    def when_tts_done_do(self, callback:callable)->None:
        """ Callback when the queue of tts messages are done """
        self._when_tts_done_callback_queue.put(callback)

    def converti(self, stringa): 
        li = list(stringa.replace(" ", "").split(","))
        return li 

    def worker(self):
        while True:
            data = self.queue.get()
            alexa_player = data["alexa_player"]
            
            """ ALEXA TYPE-METHOD """
            if data["type"] == "tts":
                if data["alexa_type"] == "tts":
                    alexa_data = {"type": "tts"}
                    __WAIT_TIME__ = 2
                else:
                    __WAIT_TIME__ = 3.5
                    alexa_data = {"type": data["alexa_type"],
                                    "method": data["alexa_method"]
                                    }

                chars = data["text"].count('')
                duration = ((chars * 0.00133) * 60) + __WAIT_TIME__ 

                """ SPEAK """
                self.log("WORKER ALEXA PLAYER = {} ".format(alexa_player))
                self.log("| CHARS = {} | DURATION = {}".format(chars,round(duration,2)))
                self.call_service(__NOTIFY__ + self.alexa_tts, data = alexa_data, target = alexa_player, message = data["text"])
                self.volume_set(alexa_player, data["volume"])

                """ Sleep and wait for the tts to finish """
                time.sleep(duration)

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting")
                """ RESTORE VOLUME """
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        self.log("VOLUME RIPROGRAMMATO: {} - {}".format(j,i))
                        # Force Set state
                        self.set_state(i, attributes = {"volume_level": j})

                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("ERRORE NEL TRY EXCEPT", level="ERROR")
                    self.error("ERRORE NEL TRY EXCEPT", level="ERROR")
                    pass # Nothing in queue
