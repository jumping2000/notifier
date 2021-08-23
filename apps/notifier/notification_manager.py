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
        #self.text_last_message = globals.get_arg(self.args, "text_last_message")
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
        if self.get_state(self.boolean_wrap_text) == 'on':
            message = self.replace_regular(message, SUB_NOTIFICHE_WRAP)
        else:
            message = self.replace_regular(message, SUB_NOTIFICHE_NOWRAP)
        return message, title

    def removekey(self, d, key):
        r = dict(d)
        del r[key]
        return r

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
        message = data["message"]
        image = data["image"]
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
            #### TELEGRAM #######################
            if item.find("telegram") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                extra_data = ""
                if str(html).lower() not in ["true","on","yes","1"]:
                    messaggio = messaggio.replace("_","\_")
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                if caption == "":
                    caption = ("{}\n{}".format(titolo,messaggio))
                if image != ""  and image.find("http") != -1:
                    extra_data = { "photo": 
                                    {"url": image,
                                    "caption": caption,
                                    "timeout": 90}
                                }
                if image != ""  and image.find("http") == -1:
                    extra_data = { "photo": 
                                    {"file": image,
                                    "caption": caption,
                                    "timeout": 90}
                                }
                if image != "":
                    self.call_service(item, message = "", data = extra_data)
                else:
                    self.call_service(item, message = messaggio, title = titolo)
            #### WHATSAPP #######################
            elif item.find("whatsapp") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                messaggio = titolo + " " + messaggio
                self.call_service( item, message = messaggio)
            #### PUSHOVER #######################
            elif item.find("pushover") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = titolo.replace("*","")
                extra_data = {}
                if image != "" and image.find("http") != -1:
                    extra_data = {"url": image}
                if image != "" and image.find("http") == -1:
                    extra_data = {"attachment": image}
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            #### PUSHBULLET #####################
            elif item.find("pushbullet") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = titolo.replace("*","")
                extra_data = {}
                if link !="":
                    message = ("{} {}".format(messaggio,link))
                if image != "" and image.find("http") != -1:
                    extra_data = {"url": image}
                if image != "" and image.find("http") == -1:
                    extra_data = {"file": image}
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            #### MAIL ###########################
            elif item.find("mail") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = titolo.replace("*","")
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                self.call_service( item, message = messaggio, title = titolo)
            #### MOBILE #########################
            elif item.find("mobile") != -1:
                titolo = title
                messaggio = message
                # messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                tts_flag = False
                extra_data = {}
                if isinstance(mobile, dict):
                    if "tts" in mobile:
                        if str(mobile.get("tts")).lower() in ["true","on","yes","1"]:
                            tts_flag = True
                        else:
                            tts_flag = False
                        extra_data = self.removekey(mobile,"tts")
                    if "image" in mobile:
                        extra_data = mobile
                if image != "":
                    extra_data.update({"image":image})
                if tts_flag:
                    if self.get_state(self.boolean_tts_clock) == 'on':
                        titolo = ("{} {}".format(timestamp, titolo + " " + messaggio))
                        messaggio = 'TTS'
                else:
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
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
        if self.get_state(self.boolean_wrap_text) == 'on':
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
