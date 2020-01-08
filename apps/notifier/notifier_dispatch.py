import appdaemon.plugins.hass.hassapi as hass
import yaml
import globals
#
# Centralizes messaging.
#
# Args:
#
# Version 1.0:
#   Initial Version

class Notifier_Dispatch(hass.Hass):

    def initialize(self):
        self.gh_tts_google_mode = globals.get_arg(self.args, "gh_tts_google_mode")
        self.gh_switch_entity = globals.get_arg(self.args, "gh_switch")
        self.gh_selected_media_player = globals.get_arg(self.args, "gh_selected_media_player")

        self.alexa_tts_alexa_type = globals.get_arg(self.args, "alexa_tts_alexa_type")
        self.alexa_tts_alexa_method = globals.get_arg(self.args, "alexa_tts_alexa_method")
        self.alexa_switch_entity = globals.get_arg(self.args, "alexa_switch")
        self.alexa_selected_media_player = globals.get_arg(self.args, "alexa_selected_media_player")

        self.ariela_switch_entity = globals.get_arg(self.args, "ariela_switch")

        self.tts_language = globals.get_arg(self.args, "tts_language")
        self.tts_period_of_day_volume = globals.get_arg(self.args, "tts_period_of_day_volume")
        self.tts_dnd = globals.get_arg(self.args, "dnd")

        self.text_notifications = globals.get_arg(self.args, "text_notifications")
        self.screen_notifications = globals.get_arg(self.args, "screen_notifications")
        self.speech_notifications = globals.get_arg(self.args, "speech_notifications")
        self.phone_notifications = globals.get_arg(self.args, "phone_notifications")

        self.text_notify = globals.get_arg(self.args, "text_notify")
        self.phone_notify = globals.get_arg(self.args, "phone_notify")
        self.priority_message = globals.get_arg(self.args, "priority_message")
        self.guest_mode = globals.get_arg(self.args, "guest_mode")

        self.persistent_notification_info = globals.get_arg(self.args, "persistent_notification_info")
        
        self.location_tracker = globals.get_arg(self.args, "location_tracker") 
        self.personal_assistant_name = globals.get_arg(self.args, "personal_assistant_name") 
        self.intercom_message_hub = globals.get_arg(self.args, "intercom_message_hub")
        self.phone_called_number = globals.get_arg(self.args, "phone_called_number")

        #### FROM SECRET FILE ####
        with open("/config/packages/secrets.yaml", 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
        self.ariela_tts_mqtt = cfg['ariela_tts_mqtt']
        self.gh_tts = cfg['tts_google']
        self.gh_notify = cfg['notify_google']
        self.phone_sip_server = cfg['sip_server_name']
        ### APP MANAGER ###
        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")
        self.phone_manager = self.get_app("Phone_Manager")
        ### LISTEN EVENT ###
        self.listen_event(self.notify_hub, "hub")

#####################################################################
    def notify_hub(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")
        ### FROM INPUT SELECT ###
        notify_name = self.get_state(self.text_notify).lower().replace(" ", "_")
        phone_notify_name = self.get_state(self.phone_notify).lower().replace(" ", "_")
        ### FROM INPUT BOOLEAN ###
        dnd_status = self.get_state(self.tts_dnd)
        location_status = self.get_state(self.location_tracker)
        guest_status = self.get_state(self.guest_mode)
        priority_status = (self.get_state(self.priority_message) == "on") or (data["priority"] == "1")
        if (self.get_state(self.priority_message) == "on"):
            self.set_state(self.priority_message, state = "off")
        #self.log("[PRIORITY]: {}".format(priority_status))
        ###
        if ((priority_status or self.get_state(self.text_notifications) == "on") and (data["location"] != "home" or location_status != "home") and data["notify"] != "0"):
            useNotification = True
        else:
            useNotification = False
        if ((priority_status or self.get_state(self.screen_notifications) == "on") and data["no_show"] != "1"):
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        if ((priority_status or self.get_state(self.speech_notifications) == "on") and data["mute"] != "1" and dnd_status == "off" and (location_status == "home" or guest_status == "on")):
            useTTS = True
        else:
            useTTS = False
        if ((priority_status or self.get_state(self.phone_notifications) == "on") and data["mute"] != "1" and dnd_status == "off"):
            usePhone = True
        else:
            usePhone = False
        ### TTS SWITCH ###
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        ariela_switch = self.get_state(self.ariela_switch_entity)
        ### SERVIZIO TTS/NOTIFY DI GOOGLE ###
        if self.get_state(self.gh_tts_google_mode) == "on":
            gh_notifica = self.gh_notify
        else:
            gh_notifica = self.gh_tts
        ### ALEXA TYPE ###
        alexa_tts_type = str(self.get_state(self.alexa_tts_alexa_type)).lower()
        alexa_tts_method = str(self.get_state(self.alexa_tts_alexa_method)).lower()
        ### FROM SCRIPT_NOTIFY ###
        if data["language"] == "":
            data.update({"language": self.get_state(self.tts_language).lower()})
        if data["media_player_google"] == "":
            data.update({"media_player_google": self.get_state(self.gh_selected_media_player)})
        if data["media_player_alexa"] == "":
            data.update({"media_player_alexa": self.get_state(self.alexa_selected_media_player)})
        if data["volume"] == "":
            data.update({"volume": self.get_state(self.tts_period_of_day_volume)})
        if data["alexa_type"] =="":
            data.update({"alexa_type": alexa_tts_type})
        if data["alexa_method"] =="":
            data.update({"alexa_method": alexa_tts_method})
        if data["called_number"] =="":
            data.update({"called_number": self.get_state(self.phone_called_number)})
        ### CALL and NOTIFY MANAGER ###
        self.log("[USE PHONE]: {}".format(usePhone))
        self.log("[phone called]: {}".format(self.phone_called_number))
        self.log("[phone called]: {}".format(self.get_state(self.phone_called_number)))
        
        if usePersistentNotification:
            self.notification_manager.send_persistent(data, self.persistent_notification_info)
        if useNotification:
            self.notification_manager.send_notify(data, notify_name, self.get_state(self.personal_assistant_name))
        if useTTS:
            if gh_switch == "on":
                self.gh_manager.speak(data, self.get_state(self.gh_tts_google_mode), gh_notifica)
            if alexa_switch == "on":
                self.alexa_manager.speak(data, self.alexa_notify)
            if ariela_switch == "on":
                self.call_service("mqtt/publish", payload = data["message"].replace("\n","").replace("   ","").replace("  "," "), topic = self.ariela_tts_mqtt, qos = 0, retain = 0)
        if usePhone:
            self.phone_manager.send_voice_call(data, phone_notify_name, self.get_state(self.phone_sip_server))

#####################################################################