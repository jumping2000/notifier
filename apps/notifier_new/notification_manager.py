import appdaemon.plugins.hass.hassapi as hass
import datetime

"""
Class Notification_Manager handles sending text to notfyng service
"""
__NOTIFY__ = "notify/"

class Notification_Manager(hass.Hass):

    def initialize(self):
        self.log("STARTED NOTIFICATION MANAGER")

    def send_notify(self, data, assistant_name: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = data["title"]
        message = data["message"]
        url = data["url"]
        _file = data["file"]
        caption = data ["caption"]
        notify_name = data["notify"]

        self.log(timestamp)
        self.log(message)

        if title !="":
            title = ("*[{} - {}]* - {}".format(assistant_name, timestamp, title))
        else:
            title = ("*[{} - {}]*".format(assistant_name, timestamp))
        
        if caption == "":
            caption = "Photo"
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
                            message = message, 
                            title = title,
                            data = extra_data)
        else:                    
            self.call_service(__NOTIFY__ + notify_name, 
                            message = message, 
                            title = title)

    def send_persistent(self, data):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        #title = data["title"]
        message = data["message"]
        self.call_service("persistent_notification/create",
                        notification_id = "info_messages",
                        message = ("{} - {}".format(timestamp, message)),
                        title = "Centro Messaggi")