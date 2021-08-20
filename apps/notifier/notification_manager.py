import hassapi as hass
import datetime
import re

"""
Class Notification_Manager handles sending text to notfyng service
"""
__NOTIFY__ = "notify/"
SUB_NOTIFICHE = [(" +"," "),("\s\s+","\n")]

class Notification_Manager(hass.Hass):

    def initialize(self):
        #self.text_last_message = globals.get_arg(self.args, "text_last_message")
        self.text_last_message = self.args["text_last_message"]
        
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
        self.log("[NT]: {}".format(nt), ascii_encode = False)
        if len(nt) == 1:
            nt[0] = notify_name if str(nt[0]).lower() in ["true","on","yes"] or nt[0] == "1" or nt[0] == 1 or nt[0] == "" else nt[0]
        self.log("[NT] 2: {}".format(nt), ascii_encode = False)
        return nt
    
    def send_notify(self, data, notify_name, assistant_name: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = data["title"]
        message = self.replace_regular(data["message"], SUB_NOTIFICHE)
        url = data["url"]
        _file = data["file"]
        caption = data["caption"]
        link = data["link"]
        html = data["html"]
        mobile = data["mobile"]
        notify_vector = self.check_notifier(self.split_device_list(str(data["notify"])),notify_name)
        #self.log("[nt-vector]: {}".format(notify_vector), ascii_encode = False)
        ### SAVE IN INPUT_TEXT.LAST_MESSAGE
        self.set_state(self.text_last_message, state = message[:245])
        for item in notify_vector:
            if item.find("notify.") == -1:
                item = __NOTIFY__ + item
            else:
                item = self.replace_regular(item,[("\.","/")])
        ### TELEGRAM ###
            if item.find("telegram") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
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
                    self.call_service( item, messagge = "", data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            ### WHATSAPP ###
            elif item.find("whatsapp") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                messaggio = titolo + " " + messaggio
                self.call_service( item, message = messaggio)
            ### PUSHOVER ###
            elif item.find("pushover") != -1:
                titolo = title
                messaggio = message 
                if titolo !="":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                else:
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                extra_data = ""
                if url !="":
                    extra_data = {"url": url}
                if _file !="":
                    extra_data["attachment"] = _file
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            ### PUSHBULLET ###
            elif item.find("pushbullet") != -1:
                titolo = title
                messaggio = message 
                if titolo !="":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                else:
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                if link !="":
                    message = ("{} {}".format(messaggio,link))
                extra_data = ""
                if url !="":
                    extra_data = {"url": url}
                elif _file !="":
                    extra_data = {"file": _file}
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            ### MAIL ###
            elif item.find("mail") != -1:
                titolo = title
                messaggio = message 
                if titolo !="":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                else:
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                extra_data = ""
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            ### MOBILE ###
            elif item.find("mobile") != -1:
                titolo = title
                messaggio = message
                self.log("[title] 1: {}".format(titolo), ascii_encode = False)
                if messaggio == "TTS":
                    titolo = ("{} {}".format(timestamp, titolo))
                elif titolo !="" and messaggio != "TTS":
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                elif messaggio != "TTS":
                    titolo = ("[{} - {}]".format(assistant_name, timestamp))
                self.log("[title] 2: {}".format(titolo), ascii_encode = False)
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                extra_data = mobile
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
    
    def send_persistent(self, data, persistent_notification_info):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            per_not_info = self.get_state(persistent_notification_info)
        except:
            per_not_info = "null"
        message = self.replace_regular(data["message"], SUB_NOTIFICHE)
        message = "{} - {}".format(timestamp, message)
        if per_not_info == "notifying":
            old_message = self.get_state(persistent_notification_info, attribute="message")
            message = old_message + "\n" + message if len(old_message) < 2500 else message
        self.call_service(
            "persistent_notification/create", notification_id="info_messages", message=message, title="Centro Messaggi"
        )
        
    def replace_regular(self, text: str, substitutions: list):
        for old, new in substitutions:
            text = re.sub(old, new, text.strip())
        return text
