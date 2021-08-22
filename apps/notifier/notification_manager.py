import hassapi as hass
import datetime
import re

"""
Class Notification_Manager handles sending text to notfyng service
"""
__NOTIFY__ = "notify/"
SUB_NOTIFICHE_NOWRAP = [("\s+"," "),(" +"," ")]
SUB_NOTIFICHE_WRAP = [(" +"," "),("\s\s+","\n")]

class Notification_Manager(hass.Hass):

    def initialize(self):
        self.text_last_message = self.args["text_last_message"]
        self.boolean_wrap_text = self.args["boolean_wrap_text"]
        self.boolean_tts_clock = self.args["boolean_tts_clock"]
    
    def prepare_text(self, html, message, title, timestamp, assistant_name):
        if str(html).lower() in ["true","on","yes","1"]:
            title = ("<b>[{} - {}] {}</b>".format(assistant_name, timestamp, title))
            title = self.replace_regular(title,[("\s<","<")])
        else:
            title = ("*[{} - {}] {}*".format(assistant_name, timestamp, title))
            title = self.replace_regular(title,[("\s\*","*")])
        return message, title

    def check_notifier(self, notifier, notify_name: str):
        nt = []
        for item in [x.strip(" ") for x in notifier]:
            nt.append(item)
        if len(nt) == 1:
            nt[0] = notify_name if str(nt[0]).lower() in ["true","on","yes"] or nt[0] == "1" or nt[0] == 1 or nt[0] == "" else nt[0]
        return nt

    def send_notify(self, data, notify_name, assistant_name: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = data["title"]
        message = ""
        if self.get_state(self.boolean_wrap_text) == 'on':
            message = self.replace_regular(data["message"], SUB_NOTIFICHE_WRAP)
        else:
            message = self.replace_regular(data["message"], SUB_NOTIFICHE_NOWRAP)
        url = data["url"]
        _file = data["file"]
        caption = data["caption"]
        link = data["link"]
        html = data["html"]
        mobile = data["mobile"]
        notify_vector = self.check_notifier(self.split_device_list(str(data["notify"])),notify_name)
        ########## SAVE IN INPUT_TEXT ###########
        self.set_state(self.text_last_message, state = message[:245])
        #########################################

        for item in notify_vector:
            if item.find("notify.") == -1:
                item = __NOTIFY__ + item
            else:
                item = self.replace_regular(item,[("\.","/")])
            if item.find("telegram") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                extra_data = ""
                if str(html).lower() not in ["true","on","yes","1"]:
                    messaggio = messaggio.replace("_","\_")
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                if caption == "":
                    caption = ("{}\n{}".format(titolo,messaggio))
                if url !="":
                    extra_data = { "photo": 
                                    {"url": url,
                                    "caption": caption,
                                    "timeout": 60}
                                }
                elif _file !="":
                    extra_data = { "photo": 
                                    {"file": _file,
                                    "caption": caption,
                                    "timeout": 60}
                                }
                if url != "" or _file != "":
                    self.call_service(item, message = "", data = extra_data)
                else:
                    self.call_service(item, message = messaggio, title = titolo)

            elif item.find("whatsapp") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                messaggio = titolo + " " + messaggio
                self.call_service( item, message = messaggio)

            elif item.find("pushover") != -1:
                titolo = title
                messaggio = message
                extra_data = ""
                if titolo !="":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                else:
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                if url !="":
                    extra_data = {"url": url}
                if _file !="":
                    extra_data["attachment"] = _file
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)

            elif item.find("pushbullet") != -1:
                titolo = title
                messaggio = message
                extra_data = ""
                if titolo !="":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                else:
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                if link !="":
                    message = ("{} {}".format(messaggio,link))
                if url !="":
                    extra_data = {"url": url}
                elif _file !="":
                    extra_data = {"file": _file}
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)

            elif item.find("mail") != -1:
                titolo = title
                messaggio = message
                extra_data = ""
                if titolo !="":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                else:
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)

            elif item.find("mobile") != -1:
                titolo = title
                messaggio = message
                extra_data = ""
                if messaggio == "TTS":
                    if self.get_state(self.boolean_tts_clock) == 'on':
                        titolo = ("{} {}".format(timestamp, titolo))
                else:
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                extra_data = mobile
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)

    def send_persistent(self, data, persistent_notification_info):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        messaggio=""
        try:
            per_not_info = self.get_state(persistent_notification_info)
        except:
            per_not_info = "null"
        if self.get_state(self.boolean_wrap_text):
            messaggio = self.replace_regular(data["message"], SUB_NOTIFICHE_WRAP)
        else:
            messaggio = self.replace_regular(data["message"], SUB_NOTIFICHE_NOWRAP)
        messaggio = ("{} - {}".format(timestamp, messaggio))
        if per_not_info == "notifying":
            old_messaggio = self.get_state(persistent_notification_info, attribute="message")
            messaggio = (old_messaggio + "\n" + messaggio) if len(old_messaggio)<2500 else messaggio
        self.call_service("persistent_notification/create", notification_id = "info_messages", message = messaggio, title = "Centro Messaggi" )

    def replace_regular(self, text: str, substitutions: list):
        for old,new in substitutions:
            text = re.sub(old, new, text.strip())
        return text
