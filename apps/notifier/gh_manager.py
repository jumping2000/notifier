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
__TTS__ = "tts/"

class GH_Manager(hass.Hass):

    def initialize(self)->None:
        self.gh_wait_time = globals.get_arg(self.args, "gh_wait_time")
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
            #self.log("SET MEDIA_PLAYER/VOLUME: {} / {}".format(item,volume))
            self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)

    def speak(self, data, gh_mode: bool, gh_notifier: str):
        """Speak the provided text through the media player"""
        self.dict_volumes = {}
        gh_player = self.converti(data["media_player_google"])
        for i in gh_player:
            self.dict_volumes[i] = float(self.get_state(globals.get_arg(self.args, "gh_restore_volume")))/100
        
        wait_time = float(self.get_state(self.gh_wait_time))
        message = data["message_tts"].replace("\n","").replace("*","").replace("   ","").replace("  "," ")
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        self.queue.put({"type": "tts", "text": message, "volume": data["volume"], "language": data["language"],
                        "gh_player": data["media_player_google"], "wait_time": wait_time, "gh_mode": gh_mode, "gh_notifier": gh_notifier})
    
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
                """ SPEECH TIME CALCULATOR """
                period = data["text"].count(', ') + data["text"].count('. ')
                words = len(data["text"].split())
                #chars = data["text"].count('')
                ### Let's hope GH will get up
                time.sleep(data["wait_time"])
                ### SPEAK
                if data["gh_mode"] == 'on':
                    self.call_service(__NOTIFY__ + data["gh_notifier"], message = data["text"])
                    duration = ((words * 0.008) * 60) + data["wait_time"] + (period*0.2)
                    # duration = (len(data["text"].split()) / 3) + data["wait_time"]
                    #Sleep and wait for the tts to finish
                    time.sleep(duration)
                else:
                    for entity in gh_player:
                        self.call_service(__TTS__ + data["gh_notifier"], entity_id = entity, message = data["text"], language = data["language"])
                        time.sleep(data["wait_time"])
                        duration = self.get_state(entity, attribute='media_duration')
                        if not duration:
                            #The TTS already played, set a small duration
                            duration = (len(data["text"].split()) / 3) + data["wait_time"]
                            #self.log("DURATION-WAIT {}:".format(duration))
                        #Sleep and wait for the tts to finish
                        time.sleep(duration)
            except:
                self.log("Errore nel ciclo principale", level="ERROR")
                self.log(sys.exc_info()) 

            self.queue.task_done()

            if self.queue.qsize() == 0:
                #self.log("QSIZE = 0 - Worker thread exiting")
                ## RESTORE VOLUME
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        #self.log("VOLUME RIPROGRAMMATO: {} - {}".format(j,i))
                        # Force Set state
                        self.set_state(i, attributes = {"volume_level": j})
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
