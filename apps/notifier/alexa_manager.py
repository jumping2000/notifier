import appdaemon.plugins.hass.hassapi as hass
import globals
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
SUB_STRING = {"/h": " all'ora","$": " dollari", "€": " euro","°C": " gradi","%": " per cento","C'è ": "c'è-"}
SUB_ALEXA = [("(\d{1})\.(\d{1})","\g<1> virgola \g<2>"),("(\d{1})\:(\d{1})","\g<1> e \g<2>"),
                ("[\s_]+", " "),("[?!:;]+", ", "),("\.+", ". "),("[\n\*]", "")]

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
        # self.log(f"Versione AppDaemon: {self.version}")

    def speak(self, data, alexa_notifier: str):
        """ SPEAK THE PROVIDED TEXT THROUGH THE MEDIA PLAYER """

        ## Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        self.queue.put({"title": data["title"], "text": data["message_tts"], "volume": data["volume"], 
                        "alexa_player": data["media_player_alexa"], "alexa_type": data["alexa_type"], 
                        "alexa_method": data["alexa_method"], "alexa_notifier": alexa_notifier,
                        "wait_time": float(self.get_state(self.wait_time))
                        })

    def volume_get(self, media_player, volume: float):
        self.dict_volumes = {}
        for i in media_player:
            self.dict_volumes[i] = self.get_state(i, attribute="volume_level", default=volume) if self.version >= '4.0.0' else volume
        # self.log(f"GET VOLUMES: {self.dict_volumes}")
        return self.dict_volumes

    def volume_set(self, media_player, volume: float):
        self.call_service("media_player/volume_set", entity_id = media_player, volume_level = volume)
        # self.log(f"SET MEDIA_PLAYER/VOLUME: {media_player} / {volume}")

    def when_tts_done_do(self, callback:callable)->None:
        """ CALLBACK WHEN THE QUEUE OF TTS MESSAGES ARE DONE """
        self._when_tts_done_callback_queue.put(callback)

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                if 'group.' in data["alexa_player"]:
                    alexa_player = self.get_state(data["alexa_player"], attribute="entity_id")
                elif 'sensor.' in data["alexa_player"]:
                    alexa_player = self.split_device_list(self.get_state(data["alexa_player"]))
                else:
                    alexa_player = self.split_device_list(data["alexa_player"])

                """ GET AND SAVE VOLUME in dict_volumes """
                self.volume_get(alexa_player, float(self.get_state(globals.get_arg(self.args, "default_restore_volume")))/100)

                if len(alexa_player) > 1:
                    # self.set_state("group.hub_media_player_alexa", state = "on", attributes = {"entity_id": alexa_player})
                    # alexa_player = "group.hub_media_player_alexa"
                    self.volume_set(alexa_player, data["volume"])

                """ ALEXA TYPE-METHOD """
                if data["alexa_type"] == "tts":
                    alexa_data = {"type": "tts"}
                else:
                    data["wait_time"] += 1.5
                    alexa_data = {"type": data["alexa_type"],
                                    "method": data["alexa_method"]
                                    }

                """ REPLACE AND CLEAN MESSAGE """
                message_clean = globals.replace_char(data["text"], SUB_STRING)
                message_clean = globals.replace_regular(message_clean, SUB_ALEXA)
                # self.log(f"TEXT: {data['text']}")
                # self.log(f"MESSAGE CLEAN: {message_clean}")

                """ SPEECH TIME CALCULATOR """
                # period = message_clean.count(', ') + message_clean.count('. ') ##+ message_clean.count(' - ')
                words = len(message_clean.split())
                chars = message_clean.count('')
                
                """ ESTIMATED TIME """
                if (chars/words) > 7 and chars > 90:
                    data["wait_time"] += 7
                    # self.log(f"ADDED EXTRA TIME: {data["wait_time"]}"), level="WARNING")
                duration = ((words * 0.007) * 60) + data["wait_time"] #+ (period*0.2)
                self.log(f"DURATION-WAIT: {duration}")

                """ SPEAK """
                self.call_service(__NOTIFY__ + data["alexa_notifier"], data = alexa_data, target = alexa_player, message = message_clean)
                self.volume_set(alexa_player, data["volume"])
                
                """ SLEEP AND WAIT FOR THE TTS TO FINISH """
                time.sleep(duration)

                """ RESTORE VOLUME """
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        # self.log(f"VOLUME RIPROGRAMMATO: {j} - {i}")
                        ## Force Set state
                        # self.set_state(i, state = "", attributes = {"volume_level": j})

            except:
                self.log("Errore nel ciclo principale", level="ERROR")
                self.log(sys.exc_info()) 

            self.queue.task_done()

            if self.queue.qsize() == 0:
                # self.log("QSIZE = 0 - Worker thread exiting \n")
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("Errore nel CallBack", level="ERROR")
                    self.log(sys.exc_info()) 
                    pass # Nothing in queue
