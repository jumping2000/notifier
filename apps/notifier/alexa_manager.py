import hassapi as hass

import re
import sys
import time
from queue import Queue
from threading import Thread

"""
    Class Alexa Manager handles sending text to speech messages to Alexa media players
    Following features are implemented:
    - Speak text to choosen media_player
    - Full queue support to manage async multiple TTS commands
    - Full wait to tts to finish to be able to supply a callback method
"""

NOTIFY = "notify/"

SUB_VOICE = [
    # ("[\s]+", " ") (r"^\s+|\s+$", "")
    # ("[?!:;]+", ","),
    ("[.]{2,}", "."),
    ("[\.](?=(((?!\}).)*\{)|[^\{\}]*\n)", ". "),
    # ("(?<!\d)\.(?!\d)", ". "),
    ("(?<!\d),(?!\d)", ", "),
    ("[\n\*]", " "),
    (" +", " "),
]

SUB_TEXT = [(" +", " "), ("\s\s+", "\n")]

VOICE_NAMES = (
    "Carla",
    "Giorgio",
    "Bianca",
    "Ivy",
    "Joanna",
    "Joey",
    "Justin",
    "Kendra",
    "Kimberly",
    "Matthew",
    "Salli",
    "Nicole",
    "Russell",
    "Amy",
    "Brian",
    "Emma",
    "Aditi",
    "Raveena",
    "Chantal",
    "Celine",
    "Lea",
    "Mathieu",
    "Hans",
    "Marlene",
    "Vicki",
    "Aditi",
    "Mizuki",
    "Takumi",
    "Vitoria",
    "Camila",
    "Ricardo",
    "Penelope",
    "Lupe",
    "Miguel",
    "Conchita",
    "Enrique",
    "Lucia",
    "Mia",
)

SUPPORTED_LANGUAGES = [
    "it-IT",
    "en-US",
    "en-CA",
    "en-AU",
    "en-GB",
    "en-IN",
    "fr-CA",
    "fr-FR",
    "de-DE",
    "hi-IN",
    "ja-JP",
    "pt-BR",
    "es-US",
    "es-ES",
    "es-MX",
]

SPEECHCON = [
    "a ah",
    "abracadabra",
    "accidenti",
    "accipicchia",
    "addio",
    "ah",
    "ahi",
    "ahia",
    "alleluia",
    "aloha",
    "alè",
    "anzi",
    "apriti sesamo",
    "argh",
    "arrivederci",
    "attenzione",
    "auguri",
    "badabim badabum",
    "badabum",
    "bah",
    "bam",
    "bang",
    "bang bang",
    "banzai",
    "basta",
    "batti cinque",
    "bau",
    "bazinga",
    "beh",
    "ben fatto",
    "bene",
    "bene bene",
    "bim bum bam",
    "bing",
    "bingo",
    "bip bip",
    "bis",
    "bla",
    "bla bla bla",
    "bleah",
    "boh",
    "boing",
    "bravo",
    "brrr",
    "bum",
    "buon appetito",
    "buon viaggio",
    "buona fortuna",
    "buonanotte",
    "buonasera",
    "buongiorno",
    "buu",
    "capito",
    "caspita",
    "cavoli",
    "cavolo",
    "cawabanga",
    "certo",
    "chissà",
    "ci stai",
    "ciao",
    "cioè",
    "ciuf ciuf",
    "clic clac",
    "come desideri",
    "come no",
    "come non detto",
    "come va",
    "come vuoi",
    "contaci",
    "coraggio",
    "così così",
    "cucù",
    "d'accordo",
    "d'oh",
    "dai",
    "davvero",
    "din don",
    "ding",
    "ding ding ding",
    "dormi bene",
    "eh",
    "eh beh",
    "eh già",
    "ehm",
    "etciù",
    "eureka",
    "evviva",
    "fiuu",
    "geronimo",
    "giusto",
    "già",
    "grande giove",
    "grazie",
    "ha",
    "hey",
    "hip hip hurrà",
    "hmm",
    "hurrà",
    "hué hué",
    "in guardia",
    "incantata",
    "kabùm",
    "ma dai",
    "magari",
    "mah",
    "mamma mia",
    "mi piace",
    "miao",
    "mistero",
    "muu",
    "nano nano",
    "non mi dire",
    "oh",
    "oh no",
    "oh oh",
    "oh sì",
    "oh yes",
    "oi",
    "oink",
    "ok",
    "okei",
    "oooh",
    "or ora",
    "ping",
    "più o meno",
    "plop",
    "pop",
    "poti poti",
    "puf",
    "pum pum",
    "puntini puntini",
    "puoi scommetterci",
    "qua qua",
    "ricevuto",
    "roger",
    "salute",
    "scacco matto",
    "scherzavo",
    "sogni d'oro",
    "splash",
    "spoiler alert",
    "su ",
    "su su",
    "swish",
    "ta dà",
    "taac",
    "tic tac",
    "tic tic tic",
    "tic-toc",
    "toc toc",
    "toh",
    "touché",
    "trallalà",
    "tsk tsk",
    "tump",
    "tweet",
    "uffa",
    "uh la là",
    "uh oh",
    "uomo in mare",
    "vabbè",
    "voilà",
    "vroom",
    "wow",
    "yippii",
    "zac",
    "zap",
]

MOBILE_PUSH = ["push", "dropin", "dropin_notification"]


class Alexa_Manager(hass.Hass):
    def initialize(self) -> None:
        self.debug = bool(self.args.get("debug", False))
        self.alexa_service = self.args.get("alexa_service")
        # self.alexa_switch_entity = self.args.get("alexa_switch")
        self.alexa_select_media_player = self.args.get("alexa_select_media_player")
        self.alexa_type = self.args.get("alexa_type")
        self.alexa_method = self.args.get("alexa_method")
        self.alexa_sensor_media_player = self.args.get("alexa_sensor_media_player")
        self.alexa_voice = self.args.get("alexa_voice")
        # self.alexa_language = self.args.get("alexa_language")
        self.prosody = self.args.get("prosody")
        self.wait_time = self.args.get("wait_time")
        self.cehck_alexa = self._checkAlexa(self.alexa_service)

        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def speak(self, alexa):
        """Speak the provided text through the media player."""
        if self.cehck_alexa is None:
            self.set_state("sensor.centro_notifiche", state="I can't find the Alexa Media component")
            return  ## self.stop_app("Alexa_Manager")
        self.lg(f"-------------------- ALEXA START DISPATCH --------------------")
        self.lg(f"FROM DISPATCH: {type(alexa)} value {alexa}")
        # remove keys with None value from a dict # TODO
        alexa = {k: v for k, v in alexa.items() if v is not None}
        self.lg(f"REMOVE [NONE] VALUE: {type(alexa)} value {alexa}")

        # TODO language ?? options: ["it-IT","en-US","en-GB","fr-FR","de-DE","ja-JP","es-ES", "nl-NL", "cn-CN"]
        default_restore_volume = float(self.get_state(self.args.get("default_restore_volume"))) / 100
        volume = float(alexa.get("volume", default_restore_volume))
        message = str(alexa.get("message", alexa["message_tts"]))

        if alexa.get("notifier"):
            alexa_player = self.player_get(alexa.get("notifier").replace("alexa_media_", "media_player."))
        else:
            alexa_player = self.player_get(alexa.get("media_player", self.get_state(self.alexa_sensor_media_player)))
        alexa_type = (
            str(alexa.get("type", self.get_state(self.alexa_type))).lower().replace("dropin", "dropin_notification")
        )

        # Push notification
        push = bool(self.check_bool(alexa.get("push")))
        if push or alexa_type in MOBILE_PUSH and message:
            message_push = self.remove_tags(self.replace_regular(message, SUB_TEXT))
            self.call_service(
                NOTIFY + self.alexa_service,
                data={"type": "push"} if push else {"type": alexa_type},
                target=alexa_player[0],  # only one device
                title=str(alexa.get("title", "")),
                message=message_push,
            )
            self.lg(f"PUSH: {push} - TYPE: {alexa_type} - MESSAGE: {message_push}")
        # Media Content # Wait 0 queues?? Restore volume?? TODO Manca un riferimento di inizio/fine riproduzione
        if alexa.get("media_content_id", ""):
            self.volume_get(alexa_player, default_restore_volume)
            self.volume_set(alexa_player, volume)
            self.call_service(
                "media_player/play_media",
                entity_id=alexa_player,
                media_content_id=alexa["media_content_id"],
                media_content_type=alexa["media_content_type"],
                # extra = {"timer": 10} ##??
            )
            self.lg(f'Content id: {alexa["media_content_id"]} - Content type: {alexa["media_content_type"]}')
        # Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done

        elif alexa_type not in MOBILE_PUSH and message:
            self.queue.put(
                {
                    "text": message,
                    "volume": volume,
                    "alexa_type": alexa_type,
                    "alexa_player": alexa_player,
                    "default_restore_volume": default_restore_volume,
                    "alexa_notifier": str(alexa.get("notifier", self.alexa_service)),
                    "wait_time": float(self.get_state(self.wait_time)),
                    "language": alexa.get("language"),  # self.get_state(self.alexa_language)),
                    "alexa_method": str(alexa.get("method", self.get_state(self.alexa_method)).lower()),
                    "alexa_voice": str(alexa.get("voice", self.get_state(self.alexa_voice))).capitalize(),
                    "alexa_audio": alexa.get("audio", None),
                    "rate": float(alexa.get("rate", self.get_state(self.prosody["rate"]))),
                    "pitch": float(alexa.get("pitch", self.get_state(self.prosody["pitch"]))),
                    "ssml_volume": float(alexa.get("ssml_volume", self.get_state(self.prosody["volume"]))),
                    "whisper": bool(self.check_bool(alexa.get("whisper", False))),
                    "ssml_switch": bool(self.check_bool(alexa.get("ssml", self.get_state(self.args["ssml_switch"])))),
                }
            )
        self.lg(f"-------------------- ALEXA  END  DISPATCH --------------------")

    def lg(self, message):
        if self.debug:
            self.log(message, level="INFO", ascii_encode=False)

    def check_bool(self, value):
        return str(value).lower() in ["true", "on", "yes", "1"]

    def inbetween(self, minv, value, maxv):
        return sorted([minv, value, maxv])[1]

    def speak_tag(self, value):  # TODO tags
        return value if "<speak>" in value or not "</" in value else f"<speak>{value}</speak>"

    def effect_tag(self, value):
        return f"<amazon:effect name='whispered'>{value}</amazon:effect>"  # if self.whisper else value

    def prosody_tag(self, value, rate, pitch, volume):
        if rate != 100.0 or pitch != 0.0 or volume != 0.0:
            rate = f"{self.inbetween(20, rate, 200)}%"  # min 20% max 200%
            pitch = f"{self.inbetween(-33.3, pitch, 50):+g}%"  # min -33.3 max +50
            volume = f"{self.inbetween(-50, volume, 4.08):+g}dB"  # max +4.08dB
            return f"<prosody rate='{rate}' pitch='{pitch}' volume='{volume}'> {value} </prosody>"
        return value

    def audio_tag(self, value: None):
        if value is None:
            return ""
        return f"<audio src='{value}'/>" if "<audio src=" not in value else value

    def lang_tag(self, value, lang):
        if lang not in SUPPORTED_LANGUAGES:
            self.lg(f"NOT SUPPORTED LANGUAGE: {lang}")
            return value
        self.lg(f"OK ADDED SSML LANGUAGE: {lang}")
        return f"<lang xml:lang='{lang}'>{value}</lang>"

    def voice_tag(self, value, name):
        if name not in VOICE_NAMES:
            self.lg(f"NOT SUPPORTED VOICE: {name}")
            return value
        self.lg(f"OK ADDED VOICE: {name}")
        return f"<voice name='{name}'>{value}</voice>"

    def say_as_tag(self, value):
        return f"<say-as interpret-as='interjection'>{value}</say-as>"

    def find_speechcon(self, value):
        substrings = sorted(SPEECHCON, key=len, reverse=True)
        regex = re.compile(r"\b" + r"\b|\b".join(map(re.escape, substrings)), re.I)
        regex_match = re.findall(regex, value)
        self.lg(f"FOUND SPEECHCON: {len(regex_match)} -> {regex_match}")
        return regex.sub(lambda m: self.say_as_tag(m.group()), value)

    def player_get(self, user_player):
        media_player = []
        user_player = self.converti(str(user_player.lower()))
        for mpu in user_player:
            if self.entity_exists(mpu):
                if "group." in mpu:
                    media_player.extend(self.get_state(mpu, attribute="entity_id"))
                elif "sensor." in mpu:
                    media_player.append(self.get_state(mpu))
                elif "media_player." in mpu:
                    media_player.append(mpu)
                else:
                    self.log(f"Invalid group, sensor or player ENTITY-ID ({mpu})", level="WARNING")
            else:
                media_player.extend([m for m in self.cehck_alexa if self.friendly_name(m).lower() in mpu]) # = friendly
        if not media_player:
            media_player.append(self.get_state(self.alexa_sensor_media_player))
            self.log(f"No media player found. I use the default one. ({media_player})", level="WARNING")
        media_player = list(set(media_player))
        self.lg(f"GET PLAYER: {media_player}")
        return media_player

    def volume_get(self, media_player, volume: float):
        """Get and save the volume of each media player."""
        self.dict_volumes = {m: self.get_state(m, attribute="volume_level", default=volume) for m in media_player}
        self.lg(f"GET VOLUMES: {self.dict_volumes}")
        return self.dict_volumes

    def volume_set(self, media_player, volume: float, **restore: False):
        if self.dict_volumes:
            for i, j in self.dict_volumes.items():
                if j != volume:
                    if restore:
                        self.call_service("media_player/volume_set", entity_id=i, volume_level=j)
                        time.sleep(1)
                        self.lg(f"OK RESTORE VOL: {i} {j} [State: {self.get_state(i, attribute='volume_level')}]")
                    else:
                        self.call_service("media_player/volume_set", entity_id=media_player, volume_level=volume)
                        self.lg(f"SET VOLUMES: {media_player} {volume}")
                        break  # time.sleep(2)

    def replace_char(self, text: str, substitutions: dict):
        """Function that does multiple string replace ops in a single pass."""
        substrings = sorted(substitutions, key=len, reverse=True)
        regex = re.compile(r"\b" + r"\b|\b".join(map(re.escape, substrings)), re.I)  # r'\b%s\b' % r'\b|\b'
        return regex.sub(lambda match: substitutions[str.lower(match.group(0))], text)  # added str.lower()

    def replace_regular(self, text: str, substitutions: list):
        for old, new in substitutions:
            text = re.sub(old, new, str(text).strip())
        return text

    def remove_tags(self, text: str):
        """Remove all tags from a string."""
        regex = re.compile("<.*?>")
        return re.sub(regex, "", str(text).strip())

    def converti(self, stringa) -> list:
        return list(stringa.replace(" ", "").split(","))
        # return self.split_device_list(stringa.replace(" ", ""))

    def when_tts_done_do(self, callback: callable) -> None:
        """Callback when the queue of tts messages are done."""
        self._when_tts_done_callback_queue.put(callback)

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                self.lg(f"WORKER: {type(data)} value {data}")
                alexa_player = data["alexa_player"]
                self.volume_get(alexa_player, data["default_restore_volume"])
                self.volume_set(alexa_player, data["volume"])  # Set volume # TODO

                # Replace and clean message
                message_clean = self.replace_regular(data["text"], SUB_VOICE)
                self.lg(f"INPUT MESSAGE: {data['text']}")
                self.lg(f"MESSAGE CLEAN: {message_clean}")

                # Speech time calculator
                words = len(message_clean.split())
                chars = message_clean.count("")

                # Alexa type-method
                if "tts" in data["alexa_type"]:
                    alexa_data = {"type": "tts"}
                else:
                    data["wait_time"] += 1.5
                    alexa_data = {
                        "type": data["alexa_type"],
                        "method": data["alexa_method"],
                    }
                # TAGS SSML
                if data["ssml_switch"] and not "<speak>" in message_clean:  # == "on"
                    voice = "Alexa" if data["alexa_voice"] not in VOICE_NAMES else data["alexa_voice"]
                    whisper = data["whisper"]
                    if "Alexa" in voice and not whisper:  # self.whisper:
                        message_clean = self.find_speechcon(message_clean)
                    message_clean = self.lang_tag(message_clean, data["language"])
                    if "Alexa" not in voice:
                        message_clean = self.voice_tag(message_clean, voice)
                    message_clean = self.audio_tag(data["alexa_audio"]) + message_clean
                    message_clean = self.prosody_tag(message_clean, data["rate"], data["pitch"], data["ssml_volume"])
                    if whisper:
                        message_clean = self.effect_tag(message_clean)
                    if "tts" in data["alexa_type"]:
                        message_clean = self.speak_tag(message_clean)
                    self.lg(f"OK SSML TAGS: {message_clean}")
                # Estimated time
                if (chars / words) > 7 and chars > 90 or data["alexa_audio"] is not None:
                    data["wait_time"] += 7
                    self.lg(f"OK ADDED EXTRA TIME: {data['wait_time']}")
                duration = ((words * 0.007) * 60) + data["wait_time"]
                #### TODO extra time for rate
                rate = self.inbetween(20, data["rate"], 200)
                if rate < 100:
                    duration += (100 - rate) * (duration / 100)
                elif rate <= 200 and rate > 100:
                    duration /= 2
                self.lg(f"DURATION-WAIT: {duration} - words: {words} - Chars: {chars}")

                # Speak >>>
                self.call_service(
                    NOTIFY + data["alexa_notifier"],
                    data=alexa_data,
                    target=alexa_player,
                    message=message_clean.strip(),
                )

                time.sleep(duration)

                # Restore volume
                self.volume_set(alexa_player, data["volume"], restore=True)  # Set volume # TODO
            except Exception as ex:
                self.log("An error occurred in Alexa Manager (worker): {}".format(ex), level="ERROR")
                self.log(f"DATA: {data}", level="ERROR")
                self.log(sys.exc_info())
                self.set_state("sensor.centro_notifiche", state=f"Alexa Manager - worker: {ex}")
            self.queue.task_done()

            if self.queue.qsize() == 0:
                try:
                    while self._when_tts_done_callback_queue.qsize() > 0:
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func()  # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("Errore nel CallBack", level="ERROR")
                    self.log(sys.exc_info())
                    self.set_state("sensor.centro_notifiche", state=f"Alexa Manager - CallBack: {ex}")
                    pass  # Nothing in queue
            self.lg("---------------------------------------------------------\n")

    def _checkAlexa(self, service):
        """ Get the media players from the alexa_media service in home assistant. """
        self.hass_config = self.get_plugin_config()
        components = self.hass_config["components"]
        if service in components:
            exclude = [service, "this_device", "_apps"]
            cehck_alexa = [
                s["service"].replace("alexa_media_", "media_player.")
                for s in self.list_services(namespace="default")
                if "notify" in s["domain"] and service in s["service"]
            ]
            self.lg(f"OK, Entity and Service: {cehck_alexa}")
            cehck_alexa = [
                s for s in cehck_alexa if self.entity_exists(s) and not any(player in s for player in exclude)
            ]
            self.lg(f"OK, found the Alexa Media component. List of media players: {cehck_alexa}")

            # """ GEt Friendly Name from Entity. """
            names = [self.friendly_name(name) for name in cehck_alexa]
            self.lg(f"FRIENDLY_NAME: {names}")
            selectoptions = self.get_state(self.alexa_select_media_player, attribute="options")
            check_alexa_options = [x for x in cehck_alexa if self.friendly_name(x) in selectoptions]
            self.lg(str(f"OPTIONS INPUT SELECT: {selectoptions} - TYPE: {type(selectoptions)}"))
            self.lg(str(f"Entity_id Media Player in Input Select {check_alexa_options}"))
            return cehck_alexa
        self.log(
            f"I can't find the Alexa Media component\n- https://github.com/custom-components/alexa_media_player",
            level="ERROR",
        )
        return
