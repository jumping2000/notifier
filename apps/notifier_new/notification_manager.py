import appdaemon.plugins.hass.hassapi as hass
import datetime
import globals

"""
Class Notification_Manager handles sending text to notfyng service
"""
__NOTIFY__ = "notify/"

class Notification_Manager(hass.Hass):

    def initialize(self):
        self.text_last_message = globals.get_arg(self.args, "text_last_message")

    def send_notify(self, data, notify_name: str, assistant_name: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = data["title"]
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ").replace("_"," ")
        url = data["url"]
        _file = data["file"]
        caption = data["caption"]
        link = data["link"]
        
        self.log = ("[MESSAGGIO]: {}".format(message))
        self.log = ("[Notifier]: {}".format(notify_name))

        if (data["notify"] != ""):
            notify_name = data["notify"]
        


        ### SAVE IN INPUT_TEXT.LAST_MESSAGE
        self.set_state(self.text_last_message, state = message[:245])

        if title !="":
            title = ("*[{} - {}] {}*".format(assistant_name, timestamp, title))
        else:
            title = ("*[{} - {}]*".format(assistant_name, timestamp))
        
        if link !="":
            message = ("{} {}".format(message,link))
        
        if caption == "":
            caption = ("{}\n{}".format(title,message))

        #self.log("[CAPTION]: {}".format(caption))

        if url !="":
            extra_data = { "photo": 
                            {"url": url,
                            "caption": caption}
                        }
        elif _file !="":
            extra_data = { "photo": 
                            {"file": _file,
                            "caption": caption}
                        }

        if url !="" or _file !="":
            self.call_service(__NOTIFY__ + notify_name, 
                            message = "",
                            data = extra_data)
        else:                    
            self.call_service(__NOTIFY__ + notify_name,
                            message = message,
                            title = title)

        if data["alexa_type"] == "push" or data["alexa_push"] =="1":
            notify_name = "alexa_media"
            self.call_service(__NOTIFY__ + notify_name, 
                            data = {"type": "push"}, 
                            target = data["media_player_alexa"], 
                            title = title, 
                            message = message)

    def send_persistent(self, data, persistent_notification_info):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            per_not_info = self.get_state(persistent_notification_info)
        except:
            per_not_info = "null"
            #self.log(sys.exc_ingo())

        message = data["message"].replace("\n","").replace("   ","").replace("  "," ").replace("_"," ")
        message = ("{} - {}".format(timestamp, message))
        if per_not_info == "notifying":
            message = self.get_state(persistent_notification_info, attribute="message") + "\n" + message

        self.call_service("persistent_notification/create",
                        notification_id = "info_messages",
                        message = message,
                        title = "Centro Messaggi")