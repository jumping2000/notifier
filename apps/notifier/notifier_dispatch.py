import hassapi as hass
import globals
import sys
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
        self.gh_tts = globals.get_arg(self.args, "tts_google")
        self.gh_notify = globals.get_arg(self.args, "notify_google")
        self.phone_sip_server = globals.get_arg(self.args, "sip_server")
        ### APP MANAGER ###
        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")
        self.phone_manager = self.get_app("Phone_Manager")
        ### LISTEN EVENT ###
        self.listen_event(self.notify_hub, "hub")

#####################################################################
    def check_flag(self, data):
        return True if str(data).lower() in ["1","true","on","yes"] else False
    
    def check_location(self, data, location):
        return True if (str(data).lower() =="" or str(data).lower()==location) else False 

    def check_notify(self, data):
        return False if str(data).lower() in ["O","false","off","no"] else True
    
    def convert(self, lst):  
        return {lst[1]: lst[3]}
    
    def createTTSdict(self,data) -> list:
        dizionario = ""
        if data == "":
            flag = False
        else:
            if "OrderedDict([(" in data:
                dizionario = self.convert(list(data.split("'")))
                if dizionario.get("mode") != None:
                    flag = self.check_flag(dizionario["mode"])
                else:
                    flag = True
            else:
                dizionario = eval(data) # convert to dict
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
        mute_flag = self.check_flag(data["mute"])
        location_flag = self.check_location(data["location"],location_status)
        notify_flag = self.check_notify(data["notify"])
        
        ### GOOGLE ####
        google_flag = self.createTTSdict(data["google"])[0]
        google = self.createTTSdict(data["google"])[1]
        ### ALEXA ####
        alexa_flag = self.createTTSdict(data["alexa"])[0]
        alexa = self.createTTSdict(data["alexa"])[1]

        ### FROM INPUT BOOLEAN ###
        dnd_status = self.get_state(self.tts_dnd)
        guest_status = self.get_state(self.guest_mode)
        priority_status = (self.get_state(self.priority_message) == "on") or priority_flag
        ### FROM INPUT SELECT ###
        notify_name = self.get_state(self.text_notify).lower().replace(" ", "_")
        phone_notify_name = self.get_state(self.phone_notify).lower().replace(" ", "_")
        ### NOTIFICATION ###
        if priority_status:
            useNotification = True
        elif self.get_state(self.text_notifications) == "on" and  data["message"] !="" and notify_flag and location_flag:
            useNotification = True
        else:
            useNotification = False
        #self.log(" Notify flag - location flag: {} - {}".format(notify_flag,location_flag))
        ### PERSISTENT ###
        if priority_status:
            usePersistentNotification = True
        elif self.get_state(self.screen_notifications) == "on" and data["message"] !="" and not noshow_flag:
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        ### TTS ###
        if priority_status:
            useTTS = True
        elif self.get_state(self.speech_notifications) == "on" and not mute_flag and dnd_status == "off" and (location_status == "home" or guest_status == "on"):
            useTTS = True
        else:
            useTTS = False
        ### PHONE ###
        if priority_status:
            usePhone = True
        elif self.get_state(self.phone_notifications) == "on" and data["message"] !="" and not mute_flag and dnd_status == "off":
            usePhone = True
        else:
            usePhone = False
        ### TTS SWITCH ###
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        ### SERVIZIO TTS/NOTIFY DI GOOGLE ###
        if self.get_state(self.gh_tts_google_mode) == "on":
            gh_notifica = self.gh_notify
        else:
            gh_notifica = self.gh_tts
        ### FROM SCRIPT_NOTIFY ###
        if data["called_number"] == "":
            data.update({"called_number": self.get_state(self.phone_called_number)})

        ###########################
        if usePersistentNotification:
            try:
                self.notification_manager.send_persistent(data, self.persistent_notification_info)
            except Exception as ex:
                self.log("An error occurred in persistent notification: {}".format(ex),level="ERROR")
                self.log(sys.exc_info()) 
                pass
        if useNotification:
            try:
                self.notification_manager.send_notify(data, notify_name, self.get_state(self.personal_assistant_name))
            except Exception as ex:
                self.log("An error occurred in text notification: {}".format(ex), level="ERROR")
                self.log(sys.exc_info())
                pass
        if useTTS:
            try:
                if gh_switch == "on" and google_flag:
                    if (data["google"]) != "":
                        if "media_player" not in google:
                            google["media_player"] = self.get_state(self.gh_selected_media_player) 
                        if "volume" not in google:
                            google["volume"] = self.get_state(self.tts_period_of_day_volume)    
                        if "media_content_id" not in google:
                            google["media_content_id"] = ""
                        if "media_content_type" not in google:
                            google["media_content_type"] = ""
                        if  "message_tts" not in google:
                            google["message_tts"] = data["message"]
                        if  "language" not in google:
                            google["language"] = self.get_state(self.tts_language).lower()                  
                    else:
                        google = {"media_player": self.get_state(self.gh_selected_media_player), "volume": self.get_state(self.tts_period_of_day_volume), "media_content_id":"", "media_content_type": "", "message_tts":""  }
                    self.gh_manager.speak(google, self.get_state(self.gh_tts_google_mode), gh_notifica)
                
                if alexa_switch == "on" and alexa_flag:
                    self.alexa_manager.speak(alexa)
            except Exception as ex:
                self.log("An error occurred in text notification: {}".format(ex),level="ERROR")
                self.log(sys.exc_info())
                pass
        if usePhone:
            try:
                self.phone_manager.send_voice_call(data, phone_notify_name, self.phone_sip_server)
            except Exception as ex:
                self.log("An error occurred in phone notification: {}".format(ex),level="ERROR")
                self.log(sys.exc_info())
                pass

        ### ripristino del priority a OFF
        if (self.get_state(self.priority_message) == "on"):
            self.set_state(self.priority_message, state = "off")

#####################################################################
#        if data["volume"] == "":
#            data.update({"volume": self.get_state(self.tts_period_of_day_volume)})
#            if data["media_player_google"] == "":
#                data.update({"media_player_google": self.get_state(self.gh_selected_media_player)})
#            if data["media_player_alexa"] == "":
#                data.update({"media_player_alexa": self.get_state(self.alexa_selected_media_player)})
#            if data["alexa_type"] =="":
#                data.update({"alexa_type": alexa_tts_type})
#            if data["alexa_method"] =="":
#                data.update({"alexa_method": alexa_tts_method})
### CALL and NOTIFY MANAGER ###
#self.log("[USE PHONE]: {}".format(usePhone))
#self.log("[PHONE CALLED]: {}".format(self.phone_called_number))
#self.log("[PHONE CALLED STATUS]: {}".format(self.get_state(self.phone_called_number)))
#self.log("[PRIORITY]: {}".format(priority_status))
#self.log("[GH NOTIFICA]: {}".format(gh_notifica))
#self.log("[GOOGLE POST]: {}".format(google))
#        if data["message"] =="":
#            data.update({"message": data["message_tts"]})