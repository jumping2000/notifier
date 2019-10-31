import appdaemon.plugins.hass.hassapi as hass
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

        self.tts_default_restore_volume = globals.get_arg(self.args,"tts_default_restore_volume")
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
        
        self.personal_assistant_name = globals.get_arg(self.args, "personal_assistant_name") 
        self.intercom_message_hub = globals.get_arg(self.args, "intercom_message_hub")

        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")

        self.listen_event(self.notify_hub, "hub")

#####################################################################
    def notify_hub(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")
        notify_name = self.get_state(self.default_notify).lower().replace(" ", "_")
        dnd = self.get_state(self.tts_dnd)

        if (self.get_state(self.text_notifications) == "on" and data["location"] != "home"):
            useNotification = True
        else:
            useNotification = False

        if (self.get_state(self.screen_notifications) == "on" and data["no_show"] != "1"):
            usePersistentNotification = True
        else:
            usePersistentNotification = False

        if (self.get_state(self.speech_notifications) == "on" and data["mute"] != "1" and dnd =="off"):
            useTTS = True
        else:
            useTTS = False

        restore_volume = float(self.get_state(self.tts_default_restore_volume)) / 100
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        
        gh_tts_mode = self.get_state(self.gh_tts_google_mode)
        alexa_tts_type = self.get_state(self.alexa_tts_alexa_type)
        alexa_tts_method = self.get_state(self.alexa_tts_alexa_method)

        if data["language"] == "":
            data.update({"language": self.get_state(self.tts_language).lower()})
        if data["media_player_google"] == "":
            data.update({"media_player_google": self.get_state(self.gh_selected_media_player)})
        if data["media_player_alexa"] == "":
            data.update({"media_player_alexa": self.get_state(self.alexa_selected_media_player)})
        if data["volume"] == "":
            data.update({"volume": self.get_state(self.tts_period_of_day_volume)})
        if data["notify"] == "":
            data.update({"notify": notify_name})
        if data["alexa_type"] =="":
            data.update({"alexa_type": alexa_tts_type})
        if data["alexa_method"] =="":
            data.update({"alexa_method": alexa_tts_method})

        if usePersistentNotification:
            self.log("##### Notifying via Persistent Notification #####")
            self.notification_manager.send_persistent(data, self.persistent_notification_info)
        if useNotification:
            self.log("##### Notifying via Telegram #####")
            self.notification_manager.send_notify(data, self.get_state(self.personal_assistant_name))
        if useTTS:
            self.log("##### Notifying via TTS #####")
            if gh_switch:
                self.gh_manager.speak(data, gh_tts_mode, restore_volume)
            if alexa_switch:
                self.alexa_manager.speak(data, restore_volume)

#####################################################################