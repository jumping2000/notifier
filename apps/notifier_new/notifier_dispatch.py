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

        self.default_notify = globals.get_arg(self.args, "default_notify")
        self.priority_message = globals.get_arg(self.args, "priority_message")
        self.guest_mode = globals.get_arg(self.args, "guest_mode")

        self.persistent_notification_info = globals.get_arg(self.args, "persistent_notification_info")
        
        self.location_tracker = globals.get_arg(self.args, "location_tracker") 
        self.personal_assistant_name = globals.get_arg(self.args, "personal_assistant_name") 
        self.intercom_message_hub = globals.get_arg(self.args, "intercom_message_hub")

        with open("/config/packages/centro_notifiche/secrets.yaml", 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
        self.ariela_tts_mqtt = cfg['ariela_tts_mqtt']
        self.gh_tts = cfg['tts_google']
        self.gh_notify = cfg['notify_google']

        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")

        self.listen_event(self.notify_hub, "hub")

#####################################################################
    def notify_hub(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")
        notify_name = self.get_state(self.default_notify).lower().replace(" ", "_")
        dnd_status = self.get_state(self.tts_dnd)
        location_status = self.get_state(self.location_tracker)
        guest_status = self.get_state(self.guest_mode)
        priority_status = self.get_state(self.priority_message)

        if (self.get_state(self.text_notifications) == "on" and (data["location"] != "home" or location_status != "home") and data["notify"] != "0"):
            useNotification = True
        else:
            useNotification = False

        if (self.get_state(self.screen_notifications) == "on" and data["no_show"] != "1"):
            usePersistentNotification = True
        else:
            usePersistentNotification = False

        if (self.get_state(self.speech_notifications) == "on" and data["mute"] != "1" and (dnd_status == "off" or priority_status == "on" ) and (location_status == "home" or guest_status == "on")):
            useTTS = True
        else:
            useTTS = False

        #restore_volume = float(self.get_state(self.tts_default_restore_volume)) / 100
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        ariela_switch = self.get_state(self.ariela_switch_entity)
        
        if self.get_state(self.gh_tts_google_mode) == "on":
            gh_notifica = self.gh_notify
        else:
            gh_notifica = self.gh_tts
        
        self.log(gh_notifica)

        alexa_tts_type = str(self.get_state(self.alexa_tts_alexa_type)).lower()
        alexa_tts_method = str(self.get_state(self.alexa_tts_alexa_method)).lower()

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

        if usePersistentNotification:
            self.notification_manager.send_persistent(data, self.persistent_notification_info)
        if useNotification:
            self.notification_manager.send_notify(data, notify_name, self.get_state(self.personal_assistant_name))
        if useTTS:
            self.log("### TTS ###")
            if gh_switch == "on":
                self.gh_manager.speak(data, self.get_state(self.gh_tts_google_mode), gh_notifica)
            if alexa_switch == "on":
                if data["alexa_type"] != "push" and data["alexa_push"] !="1":
                    self.alexa_manager.speak(data)
                if data["alexa_type"] == "push" or data["alexa_push"] =="1":
                    self.call_service("notify/alexa_media", data = {"type": "push"}, target = data["media_player_alexa"], title = data["title"], message = data["message"].replace("\n","").replace("   ","").replace("  "," "))
            if ariela_switch == "on":
                self.call_service("mqtt/publish", payload = data["message"].replace("\n","").replace("   ","").replace("  "," "), topic = self.ariela_tts_mqtt, qos = 0, retain = 0)

#####################################################################