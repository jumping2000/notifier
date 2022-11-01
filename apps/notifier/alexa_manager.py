import json
from queue import Queue
import re
from threading import Thread
import time

import hassapi as hass  # type: ignore

"""
    Class Alexa Manager handles sending text to speech messages to Alexa media players
    Following features are implemented:
    - Speak text to choosen media_player
    - Full queue support to manage async multiple TTS commands
    - Full wait to tts to finish to be able to supply a callback method
    - Mobile PUSH message
    - Media content
    - SSML, language, voice
    - Alexa Actions: Actionable Notification
"""
ALEXA_SERVICE = "alexa_media"
CUSTOM_COMPONENT_URL = "https://github.com/custom-components/alexa_media_player"

NOTIFY = "notify/"
SKILL_ID = "skill_id"
DEFAULT_VOL = "default_vol"

# Parameters
TITLE = "title"
MESSAGE = "message"
AUDIO = "audio"
EVENT_ID = "event_id"
LANGUAGE = "language"
MEDIA_CONTENT_ID = "media_content_id"
MEDIA_CONTENT_TYPE = "media_content_type"
MEDIA_PLAYER = "media_player"
METHOD = "method"
NOTIFIER = "notifier"
PITCH = "pitch"
PUSH = "push"
RATE = "rate"
SSML = "ssml"
SSML_VOL = "ssml_volume"
TYPE = "type"
VOICE = "voice"
VOLUME = "volume"
WAIT_TIME = "wait_time"
WHISPER = "whisper"
# MODE = "mode"

MOBILE_PUSH_TYPE = (PUSH, "dropin", "dropin_notification")
SUB_VOICE = [
    # ("[.]{2,}", "."),
    ("[\?\.\!,]+(?=[\?\.\!,])", ""),  # Exclude duplicate
    ("(\s+\.|\s+\.\s+|[\.])(?! )(?![^{]*})(?![^\d.]*\d)", ". "),
    ("&", " and "),  # escape
    # ("(?<!\d),(?!\d)", ", "),
    ("[\n\*]", " "),
    (" +", " "),
]
SUB_TEXT = [(" +", " "), ("\s\s+", "\n")]
SPEECHCON_IT = (
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
)
SUPPORTED_LANGUAGES = (
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
)
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


class Alexa_Manager(hass.Hass):
    def initialize(self) -> None:
        self.debug_sensor = self.args.get("debug_sensor")
        self.component_installed = self.is_component_installed(ALEXA_SERVICE)
        self.notify_services = self.list_notify_services(ALEXA_SERVICE)
        self.service2player = self.alexa_services_to_players(self.notify_services)
        self.volumes_saved = {}  # dict media players volume saved
        # Entities
        self.binary_speak = self.args.get("binary_speak")
        self.sensor_player = self.args.get("sensor_player")
        self.sensor_volume = self.args.get("sensor_day_volume")
        self.select_language = self.args.get("select_language")
        self.select_alexa_language = self.args.get("select_alexa_language")
        self.select_player = self.args.get("select_player")
        self.select_type = self.args.get("select_type")
        self.select_method = self.args.get("select_method")
        self.select_voice = self.args.get("select_voice")
        self.bool_smart_volume_set = self.args.get("bool_smart_volume_set")
        self.bool_ssml = self.args.get("bool_ssml")
        self.prosody = self.args.get("prosody")
        self.number_wait_time = self.args.get("number_wait_time")
        self.text_actionable_notification = self.args.get("actionable_notification")

        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()
        self.set_state(self.debug_sensor, state="on")

    def speak(self, alexa: dict, skill_id: str) -> None:
        """Speak the provided text through the media player."""
        if not self.service2player:
            self.set_debug_sensor("Alexa Services not found", CUSTOM_COMPONENT_URL)
            return
        self.lg(f"------ ALEXA START DISPATCH ------")
        self.lg(f"FROM DISPATCH: {type(alexa)} value {alexa}")

        # Backwards compatible message_tts
        message = str(alexa.get(MESSAGE, alexa.get("message_tts", "")))
        get_players = alexa.get(MEDIA_PLAYER, self.get_state(self.sensor_player))
        media_player = self.check_media_player(get_players)
        get_type = alexa.get(TYPE, self.get_state(self.select_type, default="tts"))
        data_type = str(get_type).lower().replace("dropin", "dropin_notification")
        default_vol = float(self.get_state(self.sensor_volume, default=10)) / 100
        volume = float(alexa.get(VOLUME, default_vol))

        alexa_lang = self.get_state(self.select_alexa_language, default="Master")
        master_lang = self.get_state(self.select_language, default="it-IT")
        final_language = alexa_lang if alexa_lang != "Master" else master_lang
        language = str(alexa.get(LANGUAGE, final_language))

        state_method = self.get_state(self.select_method, default="all")
        state_voice = self.get_state(self.select_voice, default="Alexa")
        state_wait_time = self.get_state(self.number_wait_time, default=3.0)
        state_rate = self.get_state(self.prosody[RATE], default=100.0)
        state_pitch = self.get_state(self.prosody[PITCH], default=0.0)
        state_ssml_volume = self.get_state(self.prosody[VOLUME], default=0.0)
        state_ssml = self.get_state(self.bool_ssml, default="off")

        # Actionable notification
        if event_id := alexa.get(EVENT_ID):
            self.set_textvalue(
                self.text_actionable_notification,
                json.dumps({"text": "", "event": event_id}),
            )

        # Push notification - Only one device is needed
        push = self.check_bool(alexa.get(PUSH, False))
        if (push or data_type in MOBILE_PUSH_TYPE) and message:
            message_push = self.remove_tags(self.replace_regular(message, SUB_TEXT))
            type_ = {TYPE: PUSH} if push else {TYPE: data_type}
            self.call_service(
                NOTIFY + ALEXA_SERVICE,
                data=type_,
                target=media_player[0],
                title=str(alexa.get(TITLE, "")),
                message=message_push,
            )

        # Media Content # TODO Restore volume??
        if media_content_id := alexa.get(MEDIA_CONTENT_ID):
            self.volume_get_save(media_player, volume, default_vol)
            self.volume_set(media_player, volume)
            self.call_service(
                "media_player/play_media",
                entity_id=media_player,
                media_content_id=media_content_id,
                media_content_type=alexa.get(MEDIA_CONTENT_TYPE),
                extra={"timer": alexa.get("extra", 0)},
            )

        # Queues the message to be handled async, use when_tts_done_do method
        # to supply callback when tts is done
        elif data_type not in MOBILE_PUSH_TYPE and message:
            self.queue.put(
                {
                    MESSAGE: message,
                    MEDIA_PLAYER: media_player,
                    TYPE: data_type,
                    DEFAULT_VOL: default_vol,
                    VOLUME: volume,
                    LANGUAGE: language,
                    EVENT_ID: event_id,
                    SKILL_ID: skill_id,
                    AUDIO: alexa.get(AUDIO, None),
                    NOTIFIER: str(alexa.get(NOTIFIER, ALEXA_SERVICE)),
                    METHOD: str(alexa.get(METHOD, state_method).lower()),
                    VOICE: str(alexa.get(VOICE, state_voice)).capitalize(),
                    WAIT_TIME: float(alexa.get(WAIT_TIME, state_wait_time)),
                    RATE: float(alexa.get(RATE, state_rate)),
                    PITCH: float(alexa.get(PITCH, state_pitch)),
                    SSML_VOL: float(alexa.get(SSML_VOL, state_ssml_volume)),
                    WHISPER: self.check_bool(alexa.get(WHISPER, False)),
                    SSML: self.check_bool(alexa.get(SSML, state_ssml)),
                }
            )

    def lg(self, message: str) -> None:
        self.log(str(message), level="DEBUG", ascii_encode=False)

    def check_bool(self, value) -> bool:
        """Check if user input is a boolean."""
        return str(value).lower() in ["true", "on", "yes", "1"]

    def inbetween(self, minv: float, value: float, maxv: float) -> float:
        """Check input number between minimum and maximum values range."""
        return sorted([minv, value, maxv])[1]

    def replace_regular(self, text: str, substitutions: list) -> str:
        for old, new in substitutions:
            regex = re.compile(old)
            text = re.sub(regex, new, str(text).strip())
        return text

    def str2list(self, string: str) -> list:
        """Convert string to list."""
        regex = re.compile(r"\s*,\s*")
        return self.split_device_list(re.sub(regex, ",", string))

    def has_numbers(self, string: str):
        """Check if a string contains a number."""
        numbers = re.compile("\d{2}:\d{2}|\d{4,}|\d{3,}\.\d")
        return numbers.search(string)

    def remove_tags(self, text: str) -> str:
        """Remove all tags from a string."""
        regex = re.compile("<.*?>")
        return re.sub(regex, "", str(text).strip())

    def speak_tags(self, value: str) -> str:
        """This will add a <speak> tag when using tts method"""
        return f"<speak>{value}</speak>"

    def effect_tags(self, value: str) -> str:
        """This will add a <amazon:effect> tag and applies a whispering effect."""
        return f"<amazon:effect name='whispered'>{value}</amazon:effect>"

    def prosody_tags(self, value: str, rate: float, pitch: float, volume: float) -> str:
        """This will add a <prosody> tag for volume, pitch, and rate"""
        if rate != 100.0 or pitch != 0.0 or volume != 0.0:
            r = f"{self.inbetween(20, rate, 200)}%"
            p = f"{self.inbetween(-33.3, pitch, 50):+g}%"
            v = f"{self.inbetween(-50, volume, 4.08):+g}dB"
            return f"<prosody rate='{r}' pitch='{p}' volume='{v}'> {value} </prosody>"
        return value

    def audio_tags(self, value: None) -> str:
        """This will add the <audio> tag with the given a valid URL"""
        if value is None:
            return ""
        return f"<audio src='{value}'/>" if "<audio src=" not in value else value

    def language_tags(self, value: str, lang: str) -> str:
        """This will add the <lang> tag the language model and rules to speak."""
        if lang not in SUPPORTED_LANGUAGES:
            self.lg(f"NOT SUPPORTED LANGUAGE: {lang}")
            return value
        self.lg(f"TAG SSML LANGUAGE: {lang}")
        return f"<lang xml:lang='{lang}'>{value}</lang>"

    def voice_tags(self, value: str, name: str) -> str:
        """This will add the <voice> tag with the specified Amazon Polly voice."""
        if name not in VOICE_NAMES:
            self.lg(f"NOT SUPPORTED VOICE: {name}")
            return value
        self.lg(f"TAG VOICE: {name}")
        return f"<voice name='{name}'>{value}</voice>"

    def say_as_tags(self, value: str) -> str:
        """This will add a <say-as> tag with the given speechcon for Alexa."""
        return f"<say-as interpret-as='interjection'>{value}</say-as>"

    def find_speechcon(self, value: str) -> str:
        """Find a special words and phrases that Alexa pronounces more expressively."""
        substrings = sorted(SPEECHCON_IT, key=len, reverse=True)
        regex = re.compile(r"\b" + r"\b|\b".join(map(re.escape, substrings)), re.I)
        regex_match = re.findall(regex, value)
        self.lg(f"FOUND IN SPEECHCON_IT: {len(regex_match)} -> {regex_match}")
        return regex.sub(lambda m: self.say_as_tags(m.group()), value)

    def is_component_installed(self, component: str) -> bool:
        """Check if this component is installed."""
        self.hass_config = self.get_plugin_config()
        components = self.hass_config["components"]
        is_istalled = True if component in components else False
        self.lg(f"COMPONENT INSTALLED: {is_istalled}")
        return is_istalled

    def list_notify_services(self, service: str) -> list:
        """Find all notify services of this component."""
        notify_services = [
            s.get("service")
            for s in self.list_services()
            if s.get("domain") == "notify" and service in s.get("service", "")
        ]
        self.lg(f"NOTIFY SERVICES: {notify_services}")
        return notify_services

    def alexa_services_to_players(self, alexa_notify_services) -> list:
        """convert service alexa_media_ to media_player."""
        exclude = (ALEXA_SERVICE, "this_device", "_apps", "alexa_media_last_called")
        replace_services = [
            mp.replace("alexa_media_", "media_player.")
            for mp in alexa_notify_services
            if mp not in exclude  # Extra filter
        ]
        self.lg(f"SERVICES TO MEDIA PLAYER: {replace_services}")
        service2player = [
            s
            for s in replace_services
            if self.entity_exists(s) and not any(player in s for player in exclude)
        ]
        self.lg(f"CLEAN MEDIA PLAYER LIST: {service2player}")
        return service2player

    def check_media_player(self, media_player: list) -> list:
        mplist = []
        if not isinstance(media_player, list):
            media_player = self.str2list(str(media_player.lower()))
        self.lg(f"USER PLAYER: {media_player} - TYPE: {type(media_player)}")
        media_name = self.get_state(self.select_player, attribute="options", default="")
        name2entity = self.entity_from_name(list(media_name) + media_player)
        for mp in media_player:
            if mp == "test":
                mplist = self.service2player
                self.lg(f"TEST: {mp}")
                break
            if not self.entity_exists(mp):
                self.lg(f"NOT ENTITY EXISTS: {mp}. Search by friendly name.")
                mp = name2entity.get(mp)
            if mp:
                if "group." in mp:
                    mplist.extend(self.get_state(mp, attribute="entity_id", default=""))
                elif "sensor." in mp:
                    mplist.append(self.get_state(mp))
                elif "media_player." in mp:
                    mplist.append(mp)
                else:
                    self.log(f"Invalid entity ({mp})", level="WARNING")
        if not mplist:
            mplist = self.service2player
            self.log(f"Not {media_player} found. Default {mplist}", level="WARNING")
        self.lg(f"GET PLAYER: {mplist}")
        return mplist

    def entity_from_name(self, name_list: list) -> dict:
        """Given a list of names, it takes the entity_id from the friendly_name.
        Output a dictionary key=friendly_name, value=entity_id."""
        name2entity = {}
        name_list_lower = [x.lower() for x in name_list]
        self.lg(f"NAME LIST LOWER: {name_list_lower}")
        states = self.get_state().items()
        for entity, state in states:
            friendly_name_lower = str(state["attributes"].get("friendly_name")).lower()
            if friendly_name_lower in name_list_lower:
                for name in name_list_lower:
                    if name == friendly_name_lower:
                        name2entity[friendly_name_lower] = entity
        self.lg(f"NAME-ENTITY_ID DICT: {name2entity}")
        return name2entity

    def volume_get_save(self, media_player: list, volume: float, defvol: float) -> None:
        """Get and save the volume of each media player only if different."""
        self.volumes_saved = {}
        for i in media_player:
            volume_get = self.get_state(i, attribute="volume_level", default=defvol)
            if volume_get != volume:
                self.volumes_saved[i] = volume_get
        self.lg(f"GET VOLUME: {self.volumes_saved}")

    def volume_restore(self) -> None:
        """Restore the volume of each media player."""
        if not self.volumes_saved:
            return
        for i, j in self.volumes_saved.items():
            self.call_service("media_player/volume_set", entity_id=i, volume_level=j)
            time.sleep(1)
            # Force attribute volume_level in Home assistant
            self.set_state(i, attributes={"volume_level": j})
            self.call_service("alexa_media/update_last_called", return_result=True)
            self.lg(
                f"RESTORE VOL: {i} {j} [State:"
                f" {self.get_state(i, attribute='volume_level')}]"
            )

    def volume_set(self, media_player: list, volume: float) -> None:
        """Set the volume of each media player."""
        state_smart_volume = self.get_state(self.bool_smart_volume_set, default="off")
        smart_volume = self.check_bool(state_smart_volume)
        if not self.volumes_saved and smart_volume:
            return
        media_player = list(self.volumes_saved.keys()) if smart_volume else media_player
        self.call_service(
            "media_player/volume_set", entity_id=media_player, volume_level=volume
        )
        # Not strictly necessary
        for player in media_player:
            self.set_state(player, attributes={"volume_level": volume})
            self.lg(f"SET VOLUMES: {player} {volume}")

    def set_debug_sensor(self, state: str, error: str) -> None:
        attributes = {}
        attributes["icon"] = "si:amazonalexa"
        attributes["alexa_error"] = error
        self.set_state(self.debug_sensor, state=state, attributes=attributes)

    def when_tts_done_do(self, callback: callable) -> None:
        """Callback when the queue of tts messages are done."""
        self._when_tts_done_callback_queue.put(callback)

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                self.set_state(self.binary_speak, state="on")
                self.lg(f"------ ALEXA WORKER QUEUE  ------")
                self.lg(f"WORKER: {type(data)} value {data}")
                media_player = data[MEDIA_PLAYER]
                self.volume_get_save(media_player, data[VOLUME], data[DEFAULT_VOL])
                self.volume_set(media_player, data[VOLUME])

                # Replace and clean message
                msg = self.replace_regular(data[MESSAGE], SUB_VOICE)
                self.lg(f"INPUT MESSAGE: {data[MESSAGE]}")
                self.lg(f"MESSAGE CLEAN: {msg}")

                # Speech time calculator
                words = len(self.remove_tags(msg).split())
                chars = self.remove_tags(msg).count("")
                duration = (words * 0.007) * 60

                # Extra time
                if self.has_numbers(msg):
                    duration += 4
                    self.lg(f"NUMBER! ADDED EXTRA TIME: +4")
                if (chars / words) > 7 and chars > 90 or data[AUDIO] is not None:
                    duration += 7
                    self.lg(f"ADDED EXTRA TIME: +7")

                # Alexa type-method
                if data[TYPE] == "announce":
                    duration += 1.5
                    alexa_data = {TYPE: data[TYPE], METHOD: data[METHOD]}
                else:
                    alexa_data = {TYPE: "tts"}

                # TAGS SSML
                if data[SSML] and not "<speak>" in msg:
                    voice = "Alexa" if data[VOICE] not in VOICE_NAMES else data[VOICE]
                    if voice == "Alexa" and not data[WHISPER]:
                        msg = self.find_speechcon(msg)
                    msg = self.language_tags(msg, data[LANGUAGE])
                    if voice != "Alexa":
                        msg = self.voice_tags(msg, voice)
                    msg = self.audio_tags(data[AUDIO]) + msg
                    msg = self.prosody_tags(
                        msg, data[RATE], data[PITCH], data[SSML_VOL]
                    )
                    if self.inbetween(20, data[RATE], 200) != 100:
                        if data[RATE] < 100:
                            duration += (100 - data[RATE]) * (duration / 100)
                        else:
                            duration /= 2
                    if data[WHISPER]:
                        msg = self.effect_tags(msg)
                    if data[TYPE] == "tts" and "</" in msg:
                        msg = self.speak_tags(msg)
                    self.lg(f"SSML TAGS: {msg}")

                # Estimate reading time
                duration += data[WAIT_TIME]
                self.lg(
                    f"DURATION-WAIT: {round(duration, 2)}"
                    f" - words: {words} - Chars: {chars}"
                )

                # Speak >>>
                self.call_service(
                    NOTIFY + data[NOTIFIER],
                    data=alexa_data,
                    target=media_player,
                    message=msg.strip(),
                )

                # Actionable Notificstion >>>
                if data[EVENT_ID]:
                    self.call_service(
                        "media_player/play_media",
                        entity_id=media_player,
                        media_content_id=data[SKILL_ID],
                        media_content_type="skill",
                    )
                    duration += 10
                    self.lg(f"ADDED EXTRA TIME: +10: {duration}")

                time.sleep(duration)
                self.volume_restore()

            except Exception as ex:
                self.log("Error Alexa Manager (worker): {}".format(ex), level="ERROR")
                self.log(f"DATA: {data}", level="ERROR")
                self.set_debug_sensor("Alexa Manager - Worker Error ", ex)
            self.queue.task_done()

            if self.queue.qsize() == 0:
                try:
                    while self._when_tts_done_callback_queue.qsize() > 0:
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func()  # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("Alexa Manager - CallBack Error", level="ERROR")
                    self.set_debug_sensor("Alexa Manager - CallBack Error ", ex)
                    pass  # Nothing in queue

            self.set_state(self.binary_speak, state="off")
            self.lg("------      ALEXA  END      ------\n")

    # def terminate(self):
    #     self.log("Terminating!")
