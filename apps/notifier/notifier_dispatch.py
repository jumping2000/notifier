import sys

import hassapi as hass
import helpermodule as h
import yaml

#
# Centralizes messaging.
#
# Args:
#
# Version 1.0:
#   Initial Version

class Notifier_Dispatch(hass.Hass):
    def initialize(self):
        self.gh_tts_google_mode = h.get_arg(self.args, "gh_tts_google_mode")
        self.gh_switch_entity = h.get_arg(self.args, "gh_switch")
        self.alexa_switch_entity = h.get_arg(self.args, "alexa_switch")

        self.tts_dnd = h.get_arg(self.args, "dnd")

        self.text_notifications = h.get_arg(self.args, "text_notifications")
        self.screen_notifications = h.get_arg(self.args, "screen_notifications")
        self.speech_notifications = h.get_arg(self.args, "speech_notifications")
        self.phone_notifications = h.get_arg(self.args, "phone_notifications")

        self.html_mode = h.get_arg(self.args, "html_mode")

        self.text_notify = h.get_arg(self.args, "text_notify")
        self.phone_notify = h.get_arg(self.args, "phone_notify")
        self.priority_message = h.get_arg(self.args, "priority_message")
        self.guest_mode = h.get_arg(self.args, "guest_mode")

        self.persistent_notification_info = h.get_arg(self.args, "persistent_notification_info")

        self.location_tracker = h.get_arg(self.args, "location_tracker") 
        self.personal_assistant_name = h.get_arg(self.args, "personal_assistant_name") 
        self.phone_called_number = h.get_arg(self.args, "phone_called_number")

        self.debug_sensor = h.get_arg(self.args, "debug_sensor")
        self.set_state(self.debug_sensor, state="OK")
        #### FROM SECRET FILE ###
        config = self.get_plugin_config()
        config_dir = config["config_dir"]
        self.log(f"configuration dir: {config_dir}")
        secretsFile = config_dir + "/secrets.yaml"
        with open(secretsFile, "r") as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)  # yaml.safe_load
        self.gh_tts = cfg.get("tts_google", "google_translate_say")
        self.gh_notify = cfg.get("notify_google", "google_assistant")
        self.phone_sip_server = cfg.get("sip_server_name", "fritz.box:5060")
        self.gh_tts_cloud = cfg.get("tts_google_cloud", "google_cloud")
        self.reverso_tts = cfg.get("reverso_tts", "reversotts_say")
        self.alexa_skill_id = cfg.get("notifier_alexa_actionable_skill_id", "")

        ### APP MANAGER ###
        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")
        self.phone_manager = self.get_app("Phone_Manager")
        ### LISTEN EVENT ###
        self.listen_event(self.notifier, "notifier")

#####################################################################
    def set_debug_sensor(self, state, error):
        attributes = {}
        attributes["icon"] = "mdi:wrench"
        attributes["dispatch_error"] = error
        self.set_state(self.debug_sensor, state=state, attributes=attributes)
    
    def createTTSdict(self,data) -> list:
        dizionario = ""
        if data == "" or (not h.check_notify(data)):
            flag = False
        elif str(data).lower() in ["1","true","on","yes"]:
            flag = True
            dizionario = {}
        else:
            if "OrderedDict([(" in str(data):
                dizionario = h.convert(list(data.split("'")))
                if dizionario.get("mode") != None:
                    flag = h.check_boolean(dizionario["mode"])
                else:
                    flag = True
            else:
                dizionario = data if isinstance(data, dict) else eval(data) # convert to dict
                if dizionario.get("mode") != None:
                    flag = h.check_boolean(dizionario["mode"])
                else:
                    flag = True
        return [flag,dizionario]

    def notifier(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")
        location_status = self.get_state(self.location_tracker)
        ### FLAG
        priority_flag = h.check_boolean(data["priority"])
        noshow_flag = h.check_boolean(data["no_show"])
        location_flag = h.check_location(data["location"],location_status)
        notify_flag = h.check_notify(data["notify"])
        ### GOOGLE ####
        google_flag = self.createTTSdict(data["google"])[0] if len(str(data["google"])) != 0 else False
        google = self.createTTSdict(data["google"])[1] if len(str(data["google"])) != 0 else False
        google_priority_flag = False
        if google_flag:
          if "priority" in google:
            if str(google.get("priority")).lower() in ["true","on","yes","1"]:
                google_priority_flag = True
        ### ALEXA ####
        alexa_flag = self.createTTSdict(data["alexa"])[0] if len(str(data["alexa"])) != 0 else False
        alexa = self.createTTSdict(data["alexa"])[1] if len(str(data["alexa"])) != 0 else False
        alexa_priority_flag = False
        if alexa_flag:
          if "priority" in alexa:
            if str(alexa.get("priority")).lower() in ["true","on","yes","1"]:
                alexa_priority_flag = True
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
        elif self.get_state(self.text_notifications) == "on" and  data["message"] !="" and notify_flag and location_flag:
            useNotification = True
        else:
            useNotification = False
        ### PERSISTENT ###
        if priority_status:
            usePersistentNotification = True
        elif self.get_state(self.screen_notifications) == "on" and data["message"] !="" and not noshow_flag:
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        ### TTS ###
        if priority_status or google_priority_flag or alexa_priority_flag:
            useTTS = True
        elif self.get_state(self.speech_notifications) == "on" and dnd_status == "off" and (location_status == "home" or guest_status == "on"):
            useTTS = True
        else:
            useTTS = False
        ### PHONE ###
        if priority_status:
            usePhone = True
        elif self.get_state(self.phone_notifications) == "on" and data["message"] !="" and dnd_status == "off":
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
                self.set_debug_sensor("OK", "")
            except Exception as ex:
                self.log("An error occurred in persistent notification: {}".format(ex),level="ERROR")
                self.set_debug_sensor("Error in Persistent Notification: ", ex)
                self.log(sys.exc_info()) 
        if useNotification:
            try:
                self.notification_manager.send_notify(data, notify_name, self.get_state(self.personal_assistant_name))
                self.set_debug_sensor("OK", "")
            except Exception as ex:
                self.log("An error occurred in text notification: {}".format(ex), level="ERROR")
                self.set_debug_sensor("Error in Text Notification: ", ex)
                self.log(sys.exc_info())
        if useTTS:
            if  (gh_switch == "on" or google_priority_flag) and google_flag:
                if (data["google"]) != "":
                    if "message" not in google:
                        google["message"] = data["message"]
                    if "media_content_id" not in google:
                        google["media_content_id"] = ""
                    if "media_content_type" not in google:
                        google["media_content_type"] = ""
                self.gh_manager.speak(google, self.get_state(self.gh_tts_google_mode), gh_notifica)
            if (alexa_switch == "on" or alexa_priority_flag) and alexa_flag:
                if (data["alexa"]) != "":
                    if  "message" not in alexa:
                        alexa["message"] = data["message"]
                    if  "title" not in alexa:
                        alexa["title"] = data["title"]
                self.alexa_manager.speak(alexa, self.alexa_skill_id)
        if usePhone:
            try:
                self.phone_manager.send_voice_call(data, phone_notify_name, self.phone_sip_server)
                self.set_debug_sensor("OK", "")
            except Exception as ex:
                self.log("An error occurred in phone notification: {}".format(ex),level="ERROR")
                self.set_debug_sensor("Error in Phone Notification: ", ex)
                self.log(sys.exc_info())

        ### ripristino del priority a OFF
        if (self.get_state(self.priority_message) == "on"):
            self.set_state(self.priority_message, state = "off")
