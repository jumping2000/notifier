import appdaemon.plugins.hass.hassapi as hass
import time
from queue import Queue
from threading import Thread
import sys
#from threading import Event

"""
Class TTS Manager handles sending text to speech messages to media players
Following features are implemented:
- Speak text to choosen media_player
- Speak text with greeting to choosen media_player
- Full queue support to manage async multiple TTS commands
- Full wait to tts to finish to be able to supply a callback method
"""

__NOTIFY__ = "notify/"
__WAIT_TIME__ = 1  # seconds
__TTS__ = "tts/"

class TTS_Manager(hass.Hass):

    def initialize(self) -> None:
        self.gh_tts = "google_translate_say"
        self.alexa_tts = "alexa_media"

        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()

        t = Thread(target=self.worker)
        t.daemon = True
        t.start()
        #self.event = Event()
        #self.log("Thread Alive {}, {}" .format (t.isAlive(), t.is_alive()))

    def speak(self, data, gh_switch:bool, alexa_switch: bool, alexa_type: str):
        """Speak the provided text through the media player"""
        message = data["message"].replace("  ", " ")
        message = message.replace("\n", "")
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        if gh_switch or alexa_switch: 
            self.queue.put({"type": "tts", "text": message, "volume": data["volume"], 
                    "gh_player": data["media_player_google"], "gh_switch": gh_switch, "alexa_switch": alexa_switch,
                    "alexa_player": data["media_player_alexa"], "alexa_type": data["alexa_type"], "alexa_method": data["alexa_method"] })

        #self.log("Message added to queue. Queue is empty? {}".format(self.queue.empty()))
        self.log("Queue Size is now {}".format(self.queue.qsize()))
        self.log(self.queue.queue)
    
    def volume_get(self, entity):
        """Retrieve the audio player"s volume."""
        self.log("STATO MEDIA_PLAYER: {}".format(self.get_state(entity)))
        if self.get_state(entity) == "off":
            self.log("accendo il media player: {}".format(entity))
            self.call_service("media_player/turn_on", entity_id = entity)
        return round(float(self.get_state(entity = entity, attribute="volume_level") or 0.24),2)

    def volume_set(self, entity: str, volume: float):
        self.log("MEDIA_PLAYER: {}".format(entity))
        self.call_service("media_player/volume_set", entity_id = entity, volume_level = volume)

    def when_tts_done_do(self, callback:callable)->None:
        """Callback when the queue of tts messages are done"""
        self._when_tts_done_callback_queue.put(callback)

    def converti(self, stringa): 
        li = list(stringa.replace(" ", "").split(","))
        return li 

    def worker(self):
        while True:
            data = self.queue.get()

            if (data["type"] == "tts" and data["gh_switch"] == "on"):
                #if "," in data["gh_player"]:
                #    gh_player = self.converti(data["gh_player"])
                #else:
                #    gh_player = data["gh_player"]
                gh_player = self.converti(data["gh_player"])
                for entity in gh_player:
                    ### Save current volume
                    volume_saved_gh = self.volume_get(entity)
                    self.log("VOLUME SALVATO: {} - {}".format(volume_saved_gh,entity))
                    ### Set to the desired volume
                    self.volume_set(entity, data["volume"])
                    self.log("VOLUME DESIDERATO: {}".format(data["volume"]))
                    ### SPEAK
                    time.sleep(1)
                    self.call_service(__TTS__ + self.gh_tts, entity_id = entity, message = data["text"])
                    duration = self.get_state(entity, attribute='media_duration')
                    self.log(duration)
                    if not duration:
                        #The TTS already played, set a small duration
                        duration = __WAIT_TIME__
                    #Sleep and wait for the tts to finish
                    time.sleep(duration)
                    self.call_service("media_player/volume_set", entity_id = entity, volume_level = volume_saved_gh)
                    self.set_state(entity, attributes = {"volume_level": volume_saved_gh})
                    self.log("VOLUME RIPROGRAMMATO: {} - {}".format(volume_saved_gh,entity))

            if (data["type"] == "tts" and data["alexa_switch"] == "on"):
                #if "," in data["alexa_player"]:
                #    alexa_player = self.converti(data["alexa_player"])
                #else:
                #    alexa_player = data["alexa_player"]
                alexa_player = self.converti(data["alexa_player"])
                for entity in alexa_player:
                    ### Save current volume
                    volume_saved_alexa += self.volume_get(entity)
                    self.log("VOLUME SALVATO: {}".format(volume_saved_gh))
                    ### Set to the desired volume
                    self.volume_set(entity, data["volume"])
                    self.log("VOLUME DESIDERATO: {} - {}".format(data["volume"],entity))
                    ### SPEAK
                if data["alexa_type"] == "tts":
                    alexa_data = {"type": "tts"}
                else:
                    alexa_data = {"type": data["alexa_type"],
                                    "method": data["alexa_method"]
                                    }
                self.call_service(__NOTIFY__ + self.alexa_tts, data = alexa_data, target = alexa_player, message = data["text"])
                #time.sleep(__WAIT_TIME__)
                duration = self.get_state(entity, attribute='media_duration')
                self.log(duration)
                if not duration:
                    #The TTS already played, set a small duration
                    duration = __WAIT_TIME__
                #Sleep and wait for the tts to finish                  
                time.sleep(duration)
                ##
                for entity,i in alexa_player:
                    self.call_service("media_player/volume_set", entity_id = entity, volume_level = volume_saved_alexa[i])
                    self.set_state(alexa_player, attributes = {"volume_level": volume_saved_alexa[i] })

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting")
                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("ERRORE NEL TRY EXCEPT")
                    pass # Nothing in queue

    def terminate(self):
        self.log("#### Terminate function called ####")