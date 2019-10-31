import appdaemon.plugins.hass.hassapi as hass
import time
from queue import Queue
from threading import Thread
import sys
#from threading import Event

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
        #self.event = Event()
        #self.log("Thread Alive {}, {}" .format (t.isAlive(), t.is_alive()))

    def speak(self, data, restore_volume: float):
        """Speak the provided text through the media player"""
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ")
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        self.queue.put({"type": "tts", "text": message, "volume": data["volume"], "restore_volume": restore_volume, "language": data["language"],
                        "alexa_player": data["media_player_alexa"], "alexa_type": data["alexa_type"], "alexa_method": data["alexa_method"] })

        #self.log("Message added to queue. Queue is empty? {}".format(self.queue.empty()))
        self.log("Queue Size is now {}".format(self.queue.qsize()))
        self.log(self.queue.queue)
    
    #def volume_get(self, entity):
    #    """Retrieve the audio player"s volume."""
    #    self.log("STATO MEDIA_PLAYER: {}".format(self.get_state(entity)))
    #    if self.get_state(entity) == "off":
    #        self.log("accendo il media player: {}".format(entity))
    #        self.call_service("media_player/turn_on", entity_id = entity)
    #    return round(float(self.get_state(entity = entity, attribute="volume_level") or 0.24),2)

    def volume_set(self, gh_player: list, volume: float):
        for entity in gh_player:
            ### turn on  media player
            self.log("MEDIA_PLAYER: {} ".format(entity))
            if self.get_state(entity) == "off":
                self.call_service("media_player/turn_on", entity_id = entity)
            ### Set to the desired volume
            self.log("SET MEDIA_PLAYER/VOLUME: {} / {}".format(entity,volume))
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
            restore_volume = data["restore_volume"]
            if data["type"] == "tts":
                alexa_player = self.converti(data["alexa_player"])
                ### turn on  media player and set volume
                self.volume_set(alexa_player,data["volume"])
                ### ALEXA TYPE
                if data["alexa_type"] == "tts":
                    alexa_data = {"type": "tts"}
                else:
                    alexa_data = {"type": data["alexa_type"],
                                    "method": data["alexa_method"]
                                    }
                ### SPEAK
                self.call_service(__NOTIFY__ + self.alexa_tts, data = alexa_data, target = alexa_player, message = data["text"])
                time.sleep(__WAIT_TIME__)
                duration = self.get_state(entity, attribute='media_duration')
                self.log("DURATION {}:".format(duration))
                if not duration:
                    #The TTS already played, set a small duration
                    duration = (len(data["text"].split()) / 2) + __WAIT_TIME__
                    self.log("DURATION-WAIT {}:".format(duration))
                #Sleep and wait for the tts to finish
                time.sleep(duration)
                ## RESTORE VOLUME
                for entity in alexa_player:
                    self.call_service("media_player/volume_set", entity_id = entity, volume_level = restore_volume)

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