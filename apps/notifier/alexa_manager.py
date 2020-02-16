import hassapi as hass
import globals
import sys
import time
import voluptuous as vol
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
SUB_STRING = {
    "/h": " all'ora",
    "$": " dollari",
    "€": " euro",
    "°C": " gradi",
    "%": " per cento",
    "C'è ": "c'è-",
}
SUB_ALEXA = [
    ("(\d{1})\.(\d{1})", "\g<1> virgola \g<2>"),
    ("(\d{1})\:(\d{1})", "\g<1> e \g<2>"),
    ("[?!:;]+", ","),
    ("\.+", ". "),
    ("[\n\*]", ""),
    (" +", " "),
]
# ("[\s]+", " ") (r"^\s+|\s+$", "")

# Test voluptuous
CONF_MODULE = "module"
CONF_CLASS = "class"

MODULE = "alexa_manager"
CLASS = "Alexa_Manager"
CONF_DEFAULT_RESTORE_VOLUME = "default_restore_volume"
CONF_WAIT_TIME = "wait_time"
CONF_GLOBALS = "global_dependencies"
CONF_LOG_LEVEL = "log_level"

LOG_DEBUG = "DEBUG"
LOG_ERROR = "ERROR"
LOG_INFO = "INFO"
LOG_WARNING = "WARNING"

APP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODULE): MODULE,
        vol.Required(CONF_CLASS): CLASS,
        vol.Required(CONF_DEFAULT_RESTORE_VOLUME): str,
        vol.Required(CONF_WAIT_TIME): str,
        vol.Required(CONF_GLOBALS): list,
        vol.Optional(CONF_LOG_LEVEL, default=LOG_DEBUG): vol.Any(LOG_INFO, LOG_DEBUG),
    }
)

class Alexa_Manager(hass.Hass):
    def initialize(self) -> None:
        # self.depends_on_module(globals)
        args = APP_SCHEMA(self.args)
        # Set Logging
        self._level = args.get(CONF_LOG_LEVEL)
        self.log(f"APP_SCHEMA --> {args}", level=self._level)
        self.wait_time = globals.get_arg(self.args, "wait_time")
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()
        self.version = self.get_ad_version()
        self.log(f"AppDaemon Version: {self.version}", level=self._level)

    def speak(self, data, alexa_notifier: str):
        """Speak the provided text through the media player."""

        # Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        self.queue.put(
            {
                "title": data["title"],
                "text": data["message_tts"],
                "volume": data["volume"],
                "alexa_player": data["media_player_alexa"],
                "alexa_type": data["alexa_type"],
                "alexa_method": data["alexa_method"],
                "alexa_notifier": alexa_notifier,
                "wait_time": float(self.get_state(self.wait_time)),
            }
        )

    def volume_get(self, media_player, volume: float):
        self.dict_volumes = {}
        for i in media_player:
            self.dict_volumes[i] = (
                self.get_state(i, attribute="volume_level", default=volume)
                if self.version >= "4.0.0"
                else volume
            )
        self.log(f"GET VOLUMES: {self.dict_volumes}", level=self._level)
        return self.dict_volumes

    def volume_set(self, media_player, volume: float):
        self.call_service(
            "media_player/volume_set", entity_id=media_player, volume_level=volume
        )
        self.log(
            f"SET MEDIA_PLAYER/VOLUME: {media_player} / {volume}", level=self._level
        )

    def when_tts_done_do(self, callback: callable) -> None:
        """Callback when the queue of tts messages are done."""
        self._when_tts_done_callback_queue.put(callback)

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                if "group." in data["alexa_player"]:
                    alexa_player = self.get_state(
                        data["alexa_player"], attribute="entity_id"
                    )
                elif "sensor." in data["alexa_player"]:
                    alexa_player = self.split_device_list(
                        self.get_state(data["alexa_player"])
                    )
                else:
                    alexa_player = self.split_device_list(data["alexa_player"])

                # Get and save volume in dict_volumes
                self.volume_get(
                    alexa_player,
                    float(
                        self.get_state(
                            globals.get_arg(self.args, "default_restore_volume")
                        )
                    )
                    / 100,
                )

                # Set volume
                self.volume_set(alexa_player, data["volume"])

                # Alexa type-method
                if data["alexa_type"] == "tts":
                    alexa_data = {"type": "tts"}
                else:
                    data["wait_time"] += 1.5
                    alexa_data = {
                        "type": data["alexa_type"],
                        "method": data["alexa_method"],
                    }

                # Replace and clean message
                message_clean = globals.replace_char(data["text"], SUB_STRING)
                message_clean = globals.replace_regular(message_clean, SUB_ALEXA)
                self.log(f"TEXT: {data['text']}", level=self._level, ascii_encode=False)
                self.log(
                    f"MESSAGE CLEAN: {message_clean}",
                    level=self._level,
                    ascii_encode=False,
                )

                # Speech time calculator
                # period = message_clean.count(', ') + message_clean.count('. ')
                words = len(message_clean.split())
                chars = message_clean.count("")

                # Estimated time
                if (chars / words) > 7 and chars > 90:
                    data["wait_time"] += 7
                    self.log(
                        f"ADDED EXTRA TIME: {data['wait_time']}", level=self._level
                    )
                duration = ((words * 0.007) * 60) + data["wait_time"]  # + (period*0.2)
                self.log(f"DURATION-WAIT: {duration}", level=self._level)

                # Speak
                self.call_service(
                    __NOTIFY__ + data["alexa_notifier"],
                    data=alexa_data,
                    target=alexa_player,
                    message=message_clean,
                )
                # self.volume_set(alexa_player, data["volume"])

                # Sleep and wait for the tts to finish
                time.sleep(duration)

                # Restore volume
                if self.dict_volumes:
                    for i, j in self.dict_volumes.items():
                        self.call_service(
                            "media_player/volume_set", entity_id=i, volume_level=j
                        )
                        self.log(f"VOLUME RIPROGRAMMATO: {j} - {i}", level=self._level)
                        # Force Set state
                        # self.set_state(i, state = "", attributes = {"volume_level": j})

            except:
                self.log("Errore nel ciclo principale", level="ERROR")
                self.log(sys.exc_info())

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting \n", level=self._level)
                try:
                    while self._when_tts_done_callback_queue.qsize() > 0:
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func()  # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("Errore nel CallBack", level="ERROR")
                    self.log(sys.exc_info())
                    pass  # Nothing in queue
