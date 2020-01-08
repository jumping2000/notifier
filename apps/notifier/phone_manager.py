import appdaemon.plugins.hass.hassapi as hass
import datetime
import globals

"""
Class Phone_Manager handles sending call to voice notfyng service
"""

__NOTIFY__ = "notify/"

class Phone_Manager(hass.Hass):
    def initialize(self):
        self.no_op = 1

    def send_voice_call(self, data, phone_name: str, sip_server_name: str):
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ").replace("_"," ")
        called_number= data["called_number"]
        self.log("[MESSAGGIO]: {}".format(message))
        self.log("[CALLED NUMBER]: {}".format(called_number))
        if called_number != "":
            if phone_name.find("call") == -1:
                called_number = ("sip:{}@{}".format(called_number, sip_server_name))
                self.call_service("hassio/addon_stdin", 
                        addon="89275b70_dss_voip", 
                        input = {"call_sip_uri":called_number,"message_tts":message}
                        )
            else:
                message = ("http://api.callmebot.com/start.php?user={}&text={}&lang=it-IT-Standard-A".format(called_number, message))
                self.call_service(__NOTIFY__ + phone_name,
                        message = message
                        )
