import hassapi as hass
import datetime
import globals

"""
Class Phone_Manager handles sending call to voice notfyng service
"""

__NOTIFY__ = "notify/"
SUB_TTS = [("[\*\-\[\]_\(\)\{\~\|\}]+"," ")]

class Phone_Manager(hass.Hass):
    def initialize(self):
        self.dict_lingua = {
        "it": "it-IT-Standard-A",
        "en": "en-GB-Standard-A",
        "fr": "fr-RF-Standard-A",
        "de": "de-DE-Standard-A",
        "nl": "nl-NL-Standard-A"
        }

    def send_voice_call(self, data, phone_name: str, sip_server_name: str):
        #message = data["message_tts"].replace("\n","").replace("   ","").replace("  "," ").replace("_"," ")
        message = globals.replace_regular(data["message"], SUB_TTS)
        message_tts = message.replace(" ","%20")
        called_number= data["called_number"]
        #self.log("[MESSAGGIO]: {}".format(message))
        #self.log("[CALLED NUMBER]: {}".format(called_number))
        #self.log("[PHONE_NAME]: {}".format(phone_name))
        #self.log("[SIP_SERVER]: {}".format(sip_server_name))
        #self.log("[DICT_LAN]: {}".format(self.dict_lingua))
        #self.log("[data language]: {}".format(data["language"]))
        #self.log("[LANG]: {}".format(lang))

        lang = self.dict_lingua.get(data["language"])
        if phone_name.find("voip_call") != -1:
            if called_number != "":
                called_number = ("sip:{}@{}".format(called_number, sip_server_name))
                self.call_service("hassio/addon_stdin", 
                        addon="89275b70_dss_voip", 
                        input = {"call_sip_uri":called_number,"message_tts":message}
                        )
        else:
            if called_number != "":
                url_tts = ("http://api.callmebot.com/start.php?user={}&text={}&lang={}".format(called_number, message_tts,lang))
                #self.call_service(__NOTIFY__ + phone_name, message = message)
                self.call_service("shell_command/telegram_call", url = url_tts)


