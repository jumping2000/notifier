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
        self.counter = 0

    def speak(self, data):
        """ Speak the provided text through the media player """
        default_restore_volume = float(self.get_state(globals.get_arg(self.args, "default_restore_volume")))/100
        if self.counter == 0:
            self.restore_volume = self.volume_get(data["media_player_alexa"],default_restore_volume) # default_restore_volume #
        self.counter = self.counter +1
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ")
        """ Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done """
        self.queue.put({"type": "tts", "text": message, "volume": data["volume"],
                        "alexa_player": data["media_player_alexa"], "alexa_type": data["alexa_type"], "alexa_method": data["alexa_method"] })

    def volume_get(self, media_player, volume: float):
        restore_volume = volume
        # self.dict_volumes = {} #TODO
        # gh_player = self.converti(data["media_player_google"])
        # for i in gh_player:
        #     self.dict_volumes[i] = float(self.get_state(globals.get_arg(self.args, "gh_restore_volume")))/100
        if 'group' in media_player:
            list_entity = self.get_state(media_player, attribute="entity_id")
            for entity in list_entity:
                if self.get_state(entity) == "playing":
                    vol = self.get_state(entity = entity, attribute="volume_level")
                    if vol is not None and vol > restore_volume:
                        restore_volume = vol
            self.log("GET MAX VOLUME FROM GROUP= {}\n".format(restore_volume))
        else:
            vol = self.get_state(entity = media_player, attribute="volume_level")
            if vol is not None and vol > restore_volume:
                restore_volume = vol
            self.log("GET MAX VOLUME: {} / {}\n".format(media_player,restore_volume))
        self.set_state("sensor.volume_alexa", state = restore_volume, attributes = {"friendly_name": "Volume Restore"})
        return restore_volume

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
                    __WAIT_TIME__ = 1.5
                else:
                    __WAIT_TIME__ = 2.5
                    alexa_data = {"type": data["alexa_type"],
                                    "method": data["alexa_method"]
                                    }

                caratteri = data["text"].count('')
                duration = ((caratteri * 0.00133) * 60) + __WAIT_TIME__ 

                """ SPEAK """
                self.log("WORKER ALEXA PLAYER = {} ".format(alexa_player))
                self.log("| CARATTERI = {} | DURATION = {}".format(caratteri,round(duration,2)))
                self.call_service(__NOTIFY__ + self.alexa_tts, data = alexa_data, target = alexa_player, message = data["text"])
                #self.call_service("notify/alexa_media", data = alexa_data, target = alexa_player, message = data["text"])
                self.volume_set(alexa_player, data["volume"])

                """ Sleep and wait for the tts to finish """
                time.sleep(duration)

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting")
                self.counter = 0
                
                ## TODO RESTORE VOLUME
                # if self.dict_volumes:
                #     for i,j in self.dict_volumes.items():
                #         self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                #         self.log("VOLUME RIPROGRAMMATO: {} - {}".format(j,i))

                """ RESTORE VOLUME """
                self.volume_set(alexa_player,self.restore_volume)
                self.log("RESTORE = {} | SENSOR = {} | CONTA = {}\n".format(self.restore_volume,self.get_state(entity = "sensor.volume_alexa"),self.counter))

                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("ERRORE NEL TRY EXCEPT")
                    pass # Nothing in queue

"""
TEST
                if 100 < caratteri < 150:
                    self.log("-----DURATION-2 + DUE {}:".format(duration2+2))
                    time.sleep(duration2 + 2)
                else:
                    self.log("-----DURATION-1 + 0.5 {}:".format(duration1+0.5))
                    time.sleep(duration1 + 0.5)

                #self.log("\n| DURATION     | PAROLE = {} | CARATTERI = {} \n| OLD = {} \n| (1) = {} \n| (2) = {} \n| (3) = {}".format(parole,caratteri,round(duration,2),round(duration1,2),round(duration2,2),round(duration3,2)))
                parole = len(data["text"].split()) ##+ data["text"].count('.') + data["text"].count(',') + data["text"].count('-')
                #self.log("PAROLE: {} - CARATTERI: {}".format(parole,caratteri))
                # duration = (len(data["text"].split()) / 2) + __WAIT_TIME__
                # duration1 = ((len(data["text"].split()) / 130) * 60) + __WAIT_TIME__
                # duration2 = ((parole * 0.008) * 60) + __WAIT_TIME__
"""                