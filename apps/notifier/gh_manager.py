import sys
import time
from queue import Queue
from threading import Thread

import hassapi as hass
import helpermodule as h

"""
Class TTS Manager handles sending text to speech messages to media players
Following features are implemented:
- Speak text to choosen media_player
- Full queue support to manage async multiple TTS commands
- Full wait to tts to finish to be able to supply a callback method
"""

__NOTIFY__ = "notify/"
__TTS__ = "tts/"
SUB_TTS = [("[\*\-\[\]_\(\)\{\~\|\}\s]+"," ")]
SUB_VOICE = [
    ("[\U00010000-\U0010ffff]", ""),  # strip emoji
    ("[\?\.\!,]+(?=[\?\.\!,])", ""),  # Exclude duplicate
    ("(\s+\.|\s+\.\s+|[\.])(?! )(?![^{]*})(?![^\d.]*\d)", ". "),
    ("<.*?>",""), # HTML TAG
    ("&", " and "),  # escape
    # ("(?<!\d),(?!\d)", ", "),
    ("[\n\*]", " "),
    (" +", " "),
]

CONF_MEDIA_PLAYER = "media_player"
CONF_ATTRIBUTES = "attributes"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_VOLUME_LEVEL = "volume_level"
CONF_MEDIA_CONTENT_ID = "media_content_id"
CONF_MEDIA_CONTENT_TYPE = "media_content_type"
CONF_MEDIA_DURATION = "media_duration"
CONF_MEDIA_POSITION = "media_position"
CONF_APP_NAME = "app_name"
CONF_AUTHSIG = "authSig"
CONF_DEBUG = False

class GH_Manager(hass.Hass):
    def initialize(self)->None:
        self.gh_wait_time = h.get_arg(self.args, "gh_wait_time")
        self.gh_select_media_player = h.get_arg(self.args, "gh_select_media_player")
        self.gh_sensor_media_player = h.get_arg(self.args, "gh_sensor_media_player")
        self.tts_language = h.get_arg(self.args, "tts_language")
        self.tts_period_of_day_volume = h.get_arg(self.args, "tts_period_of_day_volume")
        self.ytube_player = h.get_arg(self.args, "ytube_player")
        self.ytube_called = False
        self.debug_sensor = h.get_arg(self.args, "debug_sensor")
        self.set_state(self.debug_sensor, state="on")
        ##
        hass_config = self.get_plugin_config()
        self.tts_components = [s for s in hass_config["components"] if "tts" in s]
        self._player = {}
        ##
        for k in list(self.get_state(CONF_MEDIA_PLAYER).keys()):
            if CONF_FRIENDLY_NAME in self.get_state(CONF_MEDIA_PLAYER)[k][CONF_ATTRIBUTES]:
                self._player.update({str(self.get_state(CONF_MEDIA_PLAYER)[k][CONF_ATTRIBUTES][CONF_FRIENDLY_NAME]).lower():k})
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def check_mplayer(self, _player: dict, gh_player: list) -> list:
        """  check and save the media player entity or friendly name and return only entities """ 
        media_p = list(self.get_state(CONF_MEDIA_PLAYER).keys())
        gh = []
        for item in [x.strip(" ") for x in gh_player] :
            if item in media_p or item == "all":
                gh.append(item)
            elif _player[item] in media_p:
                gh.append(_player[item])
        return list(set(gh))

    def check_volume(self, gh_volume) -> list:
        """  check and save the media player volumes """ 
        media_state = self.get_state("media_player")
        gh = []
        for entity, state in media_state.items(): 
            friendly_name = state[CONF_ATTRIBUTES].get(CONF_FRIENDLY_NAME) if state[CONF_ATTRIBUTES].get(CONF_FRIENDLY_NAME) is not None else ""
            for item in gh_volume:
                if "gruppo" not in str(item).lower() and str(friendly_name).lower() == str(item).lower():
                    gh.append(entity)
        return gh

    def volume_set(self, gh_player: list, volume: float) -> None:
        """  set the media player volumes """ 
        if gh_player != ["all"]:
            for item in gh_player:
                self.call_service("media_player/volume_set", entity_id = item, volume_level = volume)

    def mediastate_get(self, media_player:list, volume: float) -> dict:
        """  check and save the media player attributes """ 
        dict_info_mplayer = {}
        for i in media_player:
            dict_info_mplayer[i] = {}
        for i in media_player:
            dict_info_mplayer[i][CONF_VOLUME_LEVEL] = self.get_state(i, attribute=CONF_VOLUME_LEVEL, default=volume)
            dict_info_mplayer[i]["state"] = self.get_state(i, default="idle")
            dict_info_mplayer[i][CONF_MEDIA_CONTENT_ID] = self.get_state(i, attribute=CONF_MEDIA_CONTENT_ID, default='')
            dict_info_mplayer[i][CONF_MEDIA_CONTENT_TYPE] = self.get_state(i, attribute=CONF_MEDIA_CONTENT_TYPE, default='')
            dict_info_mplayer[i][CONF_MEDIA_POSITION] = self.get_state(i, attribute=CONF_MEDIA_POSITION, default='')
            dict_info_mplayer[i][CONF_APP_NAME] = self.get_state(i, attribute=CONF_APP_NAME, default='')
            dict_info_mplayer[i][CONF_AUTHSIG] = self.get_state(i, attribute=CONF_AUTHSIG, default='')
            ##
            ##self.log("dict mplayer: {}".format(dict_info_mplayer))
        return dict_info_mplayer

    def set_debug_sensor(self, state, error):
        attributes = {}
        attributes["icon"] = "mdi:google"
        attributes["google_error"] = error
        self.set_state(self.debug_sensor, state=state, attributes=attributes)

    def check_gh(self, service, tts_components):
        """ check if tts service exist in HA """
        return next((True for comp in tts_components if comp.replace("tts", "").replace(".", "") in service), False)

    def restore_mplayer_states(self, gh_players:list, dict_info_mplayers:dict)->None:
        """  Restore volumes and media-player states """ 
        playing = False
        if dict_info_mplayers and gh_players:
            for item in gh_players:
                for key,value in dict_info_mplayers.items():
                    if item == key:
                        self.call_service("media_player/volume_set", entity_id = key, volume_level = value[CONF_VOLUME_LEVEL])
                        # Force Set state
                        #self.set_state(i, state="", attributes = {CONF_VOLUME_LEVEL: j})
                        if value["state"] == "playing": playing = True 
                        else: playing = False
                        if self.ytube_called:
                            self.call_service("ytube_music_player/call_method", entity_id = self.ytube_player, command = "interrupt_resume")
                            #self.call_service("media_player/volume_set", entity_id = k, volume_level = float(self.get_state(self.tts_period_of_day_volume))/100 )
                        elif playing and (value[CONF_AUTHSIG] !=""):
                            self.call_service("media_player/play_media", entity_id = key, media_content_id = value[CONF_MEDIA_CONTENT_ID], media_content_type = value[CONF_MEDIA_CONTENT_TYPE], authSig = value[CONF_AUTHSIG])
                            self.call_service("media_player/media_seek", entity_id = key, seek_position = value[CONF_MEDIA_POSITION])
                        elif playing and value[CONF_APP_NAME] =="Spotify":
                            self.call_service("spotcast/start", entity_id = key, force_playback = True)
                        elif playing:
                            self.call_service("media_player/play_media", entity_id = key, media_content_id = value[CONF_MEDIA_CONTENT_ID], media_content_type = value[CONF_MEDIA_CONTENT_TYPE])
                            self.call_service("media_player/media_seek", entity_id = key, seek_position = value[CONF_MEDIA_POSITION])
                        ### DEBUG #############################################################
                        if CONF_DEBUG:
                            self.log("Restore volumes, mplayer-volume precedente: {} - {}".format(item,value[CONF_VOLUME_LEVEL]))
                            self.log("Restore Music: {} - {} - {} - {} - {} - {} - {}".format(playing, key, value[CONF_MEDIA_CONTENT_ID], value[CONF_MEDIA_CONTENT_TYPE], value[CONF_MEDIA_POSITION], value[CONF_APP_NAME],value[CONF_AUTHSIG] ))
                        ### DEBUG #############################################################


    def speak(self, google, gh_mode: bool, gh_notifier: str, cfg: dict):
        """ Speak the provided text through the media player. """
        if not self.check_gh(gh_notifier,self.tts_components):
            self.set_debug_sensor(
                "I can't find the TTS Google component", "https://www.home-assistant.io/integrations/tts",
            )
            return
        if "media_player" not in google:
            google["media_player"] = self.get_state(self.gh_sensor_media_player, default=cfg.get("google_sensor"))
        if "volume" not in google:
            google["volume"] = float(self.get_state(self.tts_period_of_day_volume, default=cfg.get("day_period_volume")))/100
        if  "language" not in google:
            google["language"] = self.get_state(self.tts_language).lower()
        wait_time = float(self.get_state(self.gh_wait_time))
        message = h.replace_regular(google["message"], SUB_VOICE)
        ### DEBUG #############################################################
        if CONF_DEBUG:
            self.log("media player ricevuti: {}".format(google["media_player"]))
            self.log("volume: {}".format(google["volume"]))
            self.log("language: {}".format(google["language"]))
            self.log("wait: {}".format(wait_time))
            self.log("gh_mode: {}".format(gh_mode))
            self.log("gh_notifier: {}".format(gh_notifier))
        #######################################################################
        # queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done
        if google[CONF_MEDIA_CONTENT_ID] != "":
            try:
                self.call_service("media_extractor/play_media", entity_id = self.check_mplayer(self._player, self.split_device_list(google["media_player"])), 
                                media_content_id= google[CONF_MEDIA_CONTENT_ID], media_content_type = google[CONF_MEDIA_CONTENT_TYPE]) 
            except Exception as ex:
                self.log("An error occurred in GH Manager - Errore in media_content: {}".format(ex),level="ERROR")
                self.set_debug_sensor("GH Manager - media_content Error ", ex)
                self.log(sys.exc_info())
        #else:
        self.queue.put({"type": "tts", "text": message, "volume": google["volume"], "language": h.replace_language(google["language"]), 
                "gh_player": google["media_player"], "wait_time": wait_time, "gh_mode": gh_mode, "gh_notifier": gh_notifier,
                "select": cfg.get("google_select"), "day_vol": cfg.get("day_period_volume")})

    def when_tts_done_do(self, callback:callable)->None:
        """ Callback when the queue of tts messages are done """
        self._when_tts_done_callback_queue.put(callback)

    def worker(self):
        while True:
            try:
                data = self.queue.get()
                duration = 0
                ### SAVE DATA
                _gh_players = self.check_mplayer(self._player, self.split_device_list(data["gh_player"]))
                _gh_volumes = self.check_volume(self.get_state(self.gh_select_media_player, default=data["select"], attribute="options"))
                _dict_info_mplayers = self.mediastate_get(_gh_volumes,float(self.get_state(self.args["tts_period_of_day_volume"], default=data["day_vol"]))/100)
                ### set volume
                self.volume_set(_gh_players,data["volume"])
                ### DEBUG #############################################################
                if CONF_DEBUG:
                    self.log("media player elaborati: {}".format(_gh_players))
                    self.log("list_volumes: {}".format(_gh_volumes))
                    self.log("dict_info_mplayer: {}".format(_dict_info_mplayers))
                #######################################################################
                ### SPEAK
                if data["gh_mode"].lower()  == 'google assistant':
                    self.call_service(__NOTIFY__ + data["gh_notifier"], message = data["text"])
                else:
                    if len(_gh_players) == 1:
                        entity = _gh_players[0]
                    else:
                        entity = _gh_players
                    ############ YTUBE ###############
                    if self.get_state(self.ytube_player) == "playing" and self.get_state(entity) == "playing":
                        self.call_service("ytube_music_player/call_method", entity_id = self.ytube_player, command = "interrupt_start")
                        self.ytube_called = True
                        time.sleep(1)
                    ##### Speech time calculator #####
                    message_clean = data["text"]
                    words = len(h.remove_tags(message_clean).split())
                    chars = h.remove_tags(message_clean).count("")
                    duration = (words * 0.007) * 60
                    if h.has_numbers(message_clean):
                        duration = 4  
                    if (chars / words) > 7 and chars > 90:
                        duration = 7 
                    ##################################
                    self.call_service(__TTS__ + data["gh_notifier"], entity_id = entity, message = data["text"])#, language = data["language"])
                    if (type(entity) is list) or entity == "all" or \
                            (self.get_state(entity, attribute=CONF_MEDIA_DURATION) is None) or \
                            float(self.get_state(entity, attribute=CONF_MEDIA_DURATION)) > 60 or \
                            float(self.get_state(entity, attribute=CONF_MEDIA_DURATION)) == -1:
                        duration += data["wait_time"]
                    else:
                        duration = float(self.get_state(entity, attribute=CONF_MEDIA_DURATION)) + data["wait_time"]
                    self.log("DURATION {}: ".format(duration))
                    #Sleep and wait for the tts to finish
                    time.sleep(duration)
                    ##################################
                    if self.ytube_called:
                        self.call_service("media_player/volume_set", entity_id = entity, volume_level = 0)
                    ##################################
                    self.restore_mplayer_states(_gh_players,_dict_info_mplayers)
                    ##################################
                    self.set_state(self.debug_sensor, state="OK")

            except Exception as ex:
                self.log("An error occurred in GH Manager - Errore nel Worker: {}".format(ex),level="ERROR")
                self.log(sys.exc_info())
                self.set_debug_sensor("GH Manager - Worker Error ", ex)
            self.queue.task_done()
            if self.queue.qsize() == 0:
                #self.log("QSIZE = 0 - Worker thread exiting")
                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("An error occurred in GH Manager - Errore nel CallBack", level="ERROR")
                    self.log(sys.exc_info())
                    self.set_debug_sensor("GH Manager - CallBack Error ", ex)
                    pass # Nothing in queue
