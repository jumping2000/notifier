import hassapi as hass
import sys
import yaml

#
# Centralizes messaging.
#
# Args:
#
# Version 2.0:
#   Initial Version


class Notifier_Dispatch(hass.Hass):
    def initialize(self):
        self.gh_tts_google_mode = self.args.get("gh_tts_google_mode")
        self.gh_switch_entity = self.args.get("gh_switch")
        self.gh_selected_media_player = self.args.get("gh_selected_media_player")

        self.alexa_switch_entity = self.args.get("alexa_switch")

        self.tts_language = self.args.get("tts_language")
        self.tts_period_of_day_volume = self.args.get("tts_period_of_day_volume")
        self.tts_dnd = self.args.get("dnd")

        self.text_notifications = self.args.get("text_notifications")
        self.screen_notifications = self.args.get("screen_notifications")
        self.speech_notifications = self.args.get("speech_notifications")
        self.phone_notifications = self.args.get("phone_notifications")

        self.html_mode = self.args.get("html_mode")

        self.text_notify = self.args.get("text_notify")
        self.phone_notify = self.args.get("phone_notify")
        self.priority_message = self.args.get("priority_message")
        self.guest_mode = self.args.get("guest_mode")

        self.persistent_notification_info = self.args.get("persistent_notification_info")

        self.location_tracker = self.args.get("location_tracker")
        self.personal_assistant_name = self.args.get("personal_assistant_name")
        self.phone_called_number = self.args.get("phone_called_number")

        self.sensor = self.args.get("sensor")
        self.set_state(self.sensor, state="on")
#### FROM SECRET FILE ###
        config = self.get_plugin_config()
        config_dir = config["config_dir"]
        self.log(f"configuration dir: {config_dir}")
        secretsFile = config_dir + "/packages/secrets.yaml"
        with open(secretsFile, "r") as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)  # yaml.safe_load
        self.gh_tts = cfg.get("tts_google", "google_translate_say")
        self.gh_notify = cfg.get("notify_google", "google_assistant")
        self.phone_sip_server = cfg.get("sip_server_name", "fritz.box:5060")
        self.gh_tts_cloud = cfg.get("tts_google_cloud", "google_cloud")
        self.reverso_tts = cfg.get("reverso_tts", "reversotts_say")

        ### APP MANAGER ###
        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")
        self.phone_manager = self.get_app("Phone_Manager")
        ### LISTEN EVENT ###
        self.listen_event(self.notify_hub, "hub")

    #####################################################################
    def check_flag(self, data):
        return str(data).lower() in ["1", "true", "on", "yes"]

    def check_location(self, data, location):
        return str(data).lower() == "" or str(data).lower() == location

    def check_notify(self, data):
        return False if (str(data).lower() in ["false", "off", "no"] or data == "0" or data == 0) else True

    def convert(self, lst):
        return {lst[1]: lst[3]}

    def createTTSdict(self, data) -> list:
        dizionario = ""
        if data == "" or (not self.check_notify(data)):
            flag = False
        elif str(data).lower() in ["1","true","on","yes"]:
            flag = True
            dizionario = {}
        else:
            if "OrderedDict([(" in str(data):
                dizionario = self.convert(list(data.split("'")))
                if dizionario.get("mode") != None:
                    flag = self.check_flag(dizionario["mode"])
                else:
                    flag = True
            else:
                dizionario = data if isinstance(data, dict) else eval(data) # convert to dict
                if dizionario.get("mode") != None:
                    flag = self.check_flag(dizionario["mode"])
                else:
                    flag = True
        return [flag,dizionario]

    def notify_hub(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")

        location_status = self.get_state(self.location_tracker)
        ### FLAG
        priority_flag = self.check_flag(data["priority"])
        noshow_flag = self.check_flag(data["no_show"])
        location_flag = self.check_location(data["location"], location_status)
        notify_flag = self.check_notify(data["notify"])

        ### GOOGLE ####
        google_flag = self.createTTSdict(data["google"])[0] if len(str(data["google"])) != 0 else False
        google = self.createTTSdict(data["google"])[1] if len(str(data["google"])) != 0 else False
        ### ALEXA ####
        alexa_flag = self.createTTSdict(data["alexa"])[0] if len(str(data["alexa"])) != 0 else False
        alexa = self.createTTSdict(data["alexa"])[1] if len(str(data["alexa"])) != 0 else False

        ### FROM INPUT BOOLEAN ###
        dnd_status = self.get_state(self.tts_dnd)
        guest_status = self.get_state(self.guest_mode)
        priority_status = (self.get_state(self.priority_message) == "on") or priority_flag
        ### FROM INPUT SELECT ###
        notify_name = self.get_state(self.text_notify)
        phone_notify_name = self.get_state(self.phone_notify)
        ### NOTIFICATION ###
        if priority_status:
            useNotification = True
        elif (
            self.get_state(self.text_notifications) == "on" and data["message"] != "" and notify_flag and location_flag
        ):
            useNotification = True
        else:
            useNotification = False
        ### PERSISTENT ###
        if priority_status:
            usePersistentNotification = True
        elif self.get_state(self.screen_notifications) == "on" and data["message"] != "" and not noshow_flag:
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        ### TTS ###
        if priority_status:
            useTTS = True
        elif (
            self.get_state(self.speech_notifications) == "on"
            and dnd_status == "off"
            and (location_status == "home" or guest_status == "on")
        ):
            useTTS = True
        else:
            useTTS = False
        ### PHONE ###
        if priority_status:
            usePhone = True
        elif self.get_state(self.phone_notifications) == "on" and data["message"] != "" and dnd_status == "off":
            usePhone = True
        else:
            usePhone = False
        ### TTS SWITCH ###
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        ### SERVIZIO TTS/NOTIFY DI GOOGLE ###
        if self.get_state(self.gh_tts_google_mode) != None:
            if self.get_state(self.gh_tts_google_mode).lower() == "reverso":
                gh_notifica = self.reverso_tts
            elif self.get_state(self.gh_tts_google_mode).lower() == "google cloud":
                gh_notifica = self.gh_tts_cloud
            elif self.get_state(self.gh_tts_google_mode).lower() == "google say":
                gh_notifica = self.gh_tts
            else: 
                gh_notifica = self.gh_notify
        ### FROM SCRIPT_NOTIFY ###
        if data["called_number"] == "":
            data.update({"called_number": self.get_state(self.phone_called_number)})
        if data["html"] == "":
            data.update({"html": self.get_state(self.html_mode)})
        ###########################
        if usePersistentNotification:
            try:
                self.notification_manager.send_persistent(data, self.persistent_notification_info)
            except Exception as ex:
                self.log("An error occurred in persistent notification: {}".format(ex), level="ERROR")
                self.set_state(self.sensor, state="Error in Persistent Notification: {}".format(ex))
                self.log(sys.exc_info())
        if useNotification:
            try:
                self.notification_manager.send_notify(data, notify_name, self.get_state(self.personal_assistant_name))
            except Exception as ex:
                self.log("An error occurred in text-telegram notification: {}".format(ex), level="ERROR")
                self.set_state(self.sensor, state="Error in Text Notification: {}".format(ex))
                self.log(sys.exc_info())
        if useTTS:
            if gh_switch == "on" and google_flag:
                if (data["google"]) != "":
                    if "media_player" not in google:
                        google["media_player"] = self.get_state(self.gh_selected_media_player)
                    if "volume" not in google:
                        google["volume"] = float(self.get_state(self.tts_period_of_day_volume)) / 100
                    if "media_content_id" not in google:
                        google["media_content_id"] = ""
                    if "media_content_type" not in google:
                        google["media_content_type"] = ""
                    if "message" not in google:
                        google["message"] = data["message"]
                    if "language" not in google:
                        google["language"] = self.get_state(self.tts_language).lower()
                self.gh_manager.speak(google, self.get_state(self.gh_tts_google_mode), gh_notifica)
            if alexa_switch == "on" and alexa_flag:
                if (data["alexa"]) != "":
                    if "message" not in alexa:
                        alexa["message"] = data["message"]
                    if "title" not in alexa:
                        alexa["title"] = data["title"]
                    if "volume" not in alexa:
                        alexa["volume"] = float(self.get_state(self.tts_period_of_day_volume)) / 100
                    if "language" not in alexa:
                        alexa["language"] = self.get_state(self.tts_language)
                self.alexa_manager.speak(alexa)
        if usePhone:
            try:
                language = self.get_state(self.tts_language)
                self.phone_manager.send_voice_call(data, phone_notify_name, self.phone_sip_server, language)
            except Exception as ex:
                self.log("An error occurred in phone notification: {}".format(ex), level="ERROR")
                self.set_state(self.sensor, state="Error in Phone Notification: {}".format(ex))
                self.log(sys.exc_info())
        ### ripristino del priority a OFF
        if self.get_state(self.priority_message) == "on":
            self.set_state(self.priority_message, state="off")
