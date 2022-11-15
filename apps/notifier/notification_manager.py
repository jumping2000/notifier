import hassapi as hass
import datetime
#
import helpermodule as h
"""
Class Notification_Manager handles sending text to notfyng service
"""
__NOTIFY__ = "notify/"
SUB_NOTIFICHE_NOWRAP = [("\s+"," "),(" +"," ")]
SUB_NOTIFICHE_WRAP = [(" +"," "),("\s\s+","\n")]
SUB_NOTIFIER =  [("\s+","_"),("\.","/")]
SUB_REMOVE_SPACE = [("\s*,\s*",",")]

class Notification_Manager(hass.Hass):

    def initialize(self):
        #self.text_last_message = globals.get_arg(self.args, "text_last_message")
        self.text_last_message = h.get_arg(self.args, "text_last_message")
        self.boolean_wrap_text = h.get_arg(self.args, "boolean_wrap_text")
        self.boolean_tts_clock = h.get_arg(self.args, "boolean_tts_clock")
    
    def prepare_text(self, html, message, title, timestamp, assistant_name):
        if str(html).lower() in ["true","on","yes","1"]:
            title = ("<b>[{} - {}] {}</b>".format(assistant_name, timestamp, title))
            title = h.replace_regular(title,[("\s<","<")])
        else:
            title = ("*[{} - {}] {}*".format(assistant_name, timestamp, title))
            title = h.replace_regular(title,[("\s\*","*")])
        if self.get_state(self.boolean_wrap_text) == 'on':
            message = h.replace_regular(message, SUB_NOTIFICHE_WRAP)
        else:
            message = h.replace_regular(message, SUB_NOTIFICHE_NOWRAP)
        return message, title

    def check_notifier(self, notifier, notify_name):
        notifier_list = []
        notify_name_list = []
        notifier_vector = []
        for item in [x.strip(" ") for x in notifier]:
            notifier_vector.append(item.lower())
            notifier_list.append(item.lower())
        for item in [x.strip(" ") for x in notify_name]:
            notifier_vector.append(item.lower())
            notify_name_list.append(item.lower())
        if any(i in notifier_vector for i in ["1","true","on",1,""]):
            notifier_vector.clear()
            notifier_vector = notify_name_list
        else:
            notifier_vector.clear()
            notifier_vector = notifier_list
        return notifier_vector

    def send_notify(self, data, notify_name, assistant_name: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = data["title"]
        message = data["message"]
        target = data["target"] if "target" in data else ""
        image = data["image"]
        caption = data["caption"]
        link = data["link"]
        html = data["html"]
        priority = data["priority"]
        telegram = data["telegram"] if "telegram" in data else ""
        pushover = data["pushover"] if "pushover" in data else ""
        mobile = data["mobile"] if "mobile" in data else ""
        discord = data["discord"] if "discord" in data else ""
        whatsapp_addon = data["whatsapp"] if "whatsapp" in data else "" 
        notify_vector = self.check_notifier(h.return_array(h.replace_regular(data["notify"], SUB_REMOVE_SPACE)),self.split_device_list(str(notify_name)))
        #self.log("[NOTIFY_VECTOR]: {}".format(notify_vector), ascii_encode = False)
        ## target ##
        target_vector = []
        if target !="":
            target_vector = h.return_array(h.replace_regular(target, SUB_REMOVE_SPACE))
        ########## SAVE IN INPUT_TEXT ###########
        self.set_state(self.text_last_message, state = message[:245])
        #########################################
        if isinstance(whatsapp_addon, dict):
            notify_vector.append("whatsapp_addon")
        #########################################
        for item in notify_vector:
            if item.find("notify.") == -1:
                item = __NOTIFY__ + str(h.replace_regular(item,SUB_NOTIFIER)).lower()
            else:
                item = str(h.replace_regular(item,SUB_NOTIFIER)).lower()
            #### TELEGRAM #######################
            if item.find("telegram") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                extra_data = {}
                if isinstance(telegram, dict):
                    extra_data = telegram
                if caption == "":
                    caption = ("{}\n{}".format(titolo,messaggio))
                if image != ""  and image.find("http") != -1:
                    url_data = {"url": image,
                                "caption": caption,
                                "timeout":90 }
                    extra_data.update({"photo":url_data})
                if image != ""  and image.find("http") == -1:
                    file_data = {"file": image,
                                "caption": caption,
                                "timeout":90 }
                    extra_data.update({"photo":file_data})
                #self.log("[EXTRA-DATA]: {}".format(extra_data), ascii_encode = False)
                if str(html).lower() not in ["true","on","yes","1"]:
                    messaggio = messaggio.replace("_","\_")
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                if image != "":
                    self.call_service(item, message = "", data = extra_data)
                elif extra_data:
                    self.call_service(item, message = messaggio, title = titolo, data = extra_data)
                else: 
                    self.call_service(item, message = messaggio, title = titolo)
            #### WHATSAPP ADDON #################
            elif item.find("whatsapp_addon") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                messaggio = titolo + " " + messaggio
                extra_data = {}
                if isinstance(whatsapp_addon, dict):
                    messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                    messaggio = titolo + " " + messaggio
                    if caption == "":
                        caption = messaggio
                    extra_data = whatsapp_addon
                    if image != "":
                        extra_data.update({"body":
                                            {"image": {"url": image},
                                             "caption": caption
                                            }
                                        })
                        self.call_service("whatsapp/send_message", **extra_data)
                    elif "body" in extra_data:
                        #self.log("[EXTRA-DATA]: {}".format(extra_data), ascii_encode = False)
                        self.call_service("whatsapp/send_message", **extra_data) 
                    else:
                        extra_data.update({"body":
                                            {"text": messaggio }
                                        })
                        #self.log("[EXTRA-DATA_ELSE]: {}".format(extra_data), ascii_encode = False)
                        self.call_service("whatsapp/send_message", **extra_data)                   
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
                if isinstance(pushover, dict):
                    extra_data = pushover
                    if image != "" and image.find("http") != -1:
                        extra_data.update({"url":image})
                    if image != "" and image.find("http") == -1:
                        extra_data.update({"attachment":image})
                    if priority != "":
                        extra_data.update({"priority":priority})
                if extra_data and target_vector:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data, target = target_vector)
                elif extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                elif target_vector:
                    self.call_service( item, message = messaggio, title = titolo, target = target_vector)                
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            #### PUSHBULLET #####################
            elif item.find("pushbullet") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = titolo.replace("*","")
                extra_data = {}
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                if image != "" and image.find("http") != -1 and image.find(".") != -1:
                    extra_data.update({"file_url": image})
                if image != "" and image.find("http") != -1:
                    extra_data.update({"url": image})
                if image != "" and image.find("http") == -1:
                    extra_data.update({"file": image})
                if extra_data and target_vector:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data, target = target_vector)
                elif extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                elif target_vector:
                    self.call_service( item, message = messaggio, title = titolo, target = target_vector)                
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            #### DISCORD ########################
            elif item.find("discord") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                extra_data = {}
                if isinstance(discord, dict):
                    if "embed" in discord:
                        extra_data = discord
                        extra_data.update({"title": titolo.replace("*","")})
                        extra_data.update({"description": messaggio})
                        if link !="":
                            extra_data.update({"url":link})
                        if image != "":
                            extra_data.update({"images":image.replace("config/www","local")})
                    elif "images" in discord:
                        extra_data = discord
                        messaggio = titolo.replace("*","") + " " + messaggio
                if extra_data and "embed" in discord and target_vector:
                    self.call_service( item, message = "", data = extra_data, target = target_vector) 
                elif extra_data and "images" in discord and target_vector:
                    self.call_service( item, message = messaggio, data = extra_data, target = target_vector) 
                elif extra_data and "embed" in discord:
                    self.call_service( item, message = "", data = extra_data)
                elif extra_data and "images" in discord:
                    self.call_service( item, message = messaggio, data = extra_data)
                elif target_vector:
                    self.call_service( item, message = messaggio, target = target_vector)
                else:
                    self.call_service( item, message = messaggio)
            #### MAIL ###########################
            elif item.find("mail") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = titolo.replace("*","")
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                self.call_service( item, message = messaggio, title = titolo)
            #### MOBILE #########################
            elif item.find("mobile") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = title
                tts_flag = False
                extra_data = {}
                if isinstance(mobile, dict):
                    if "tts" in mobile and "tts_text" not in mobile:
                        if str(mobile.get("tts")).lower() in ["true","on","yes","1"]:
                            tts_flag = True
                            extra_data = h.remove_key(mobile,"tts")
                            if self.get_state(self.boolean_tts_clock) == 'on':
                                temp = ("{} {}".format(timestamp, titolo + " " + messaggio))
                            else:
                                temp = ("{}".format(titolo + " " + messaggio))
                            extra_data.update({"tts_text": temp})
                        else:
                            tts_flag = False
                            extra_data = h.remove_key(mobile,"tts")
                    elif "tts_text" in mobile:
                        tts_flag = True
                        if self.get_state(self.boolean_tts_clock) == 'on':
                            temp = ("{} {}".format(timestamp, str(mobile.get("tts_text"))))
                        else:
                            temp = ("{}".format(str(mobile.get("tts_text"))))
                        extra_data = mobile
                        extra_data.update({"tts_text": temp})
                    else:
                        extra_data = mobile
                if tts_flag:
                    messaggio = "TTS"
                else:
                    titolo = ("[{} - {}] {}".format(assistant_name, timestamp, titolo))
                if image != "":
                    extra_data.update({"image":image.replace("config/www","local")})
                if link !="":
                    messaggio = ("{} {}".format(messaggio,link))
                if extra_data:
                    self.call_service( item, message = messaggio, title = titolo, data = extra_data)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            #### GOTIFY #########################
            elif item.find("gotify") != -1:
                messaggio, titolo = self.prepare_text(html, message, title, timestamp, assistant_name)
                titolo = titolo.replace("*","")
                if link !="" and caption !="":
                    messaggio = ("{} [{}]({})".format(messaggio,caption,link))
                elif link !="" :
                    messaggio = ("{} [{}]({})".format(messaggio,link,link)) 
                if image !="" and caption !="":
                    messaggio = ("{} ![{}]({})".format(messaggio,caption,image))
                elif image !="" :
                    messaggio = ("{} ![{}]({})".format(messaggio,image,image)) 
                if priority !="":
                    self.call_service( item, message = messaggio, title = titolo, target = priority)
                else:
                    self.call_service( item, message = messaggio, title = titolo)
            #### other ##########################
            else:
                if title != "":
                    title = "[{} - {}] {}".format(assistant_name, timestamp, title)
                else:
                    title = "[{} - {}]".format(assistant_name, timestamp)
                if link !="":
                    message = ("{} {}".format(message,link))
                self.call_service(item, message=message, title=title)

    def send_persistent(self, data, persistent_notification_info):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        messaggio=""
        try:
            per_not_info = self.get_state(persistent_notification_info)
        except:
            per_not_info = "null"
        if self.get_state(self.boolean_wrap_text) == 'on':
            messaggio = h.replace_regular(data["message"], SUB_NOTIFICHE_WRAP)
        else:
            messaggio = h.replace_regular(data["message"], SUB_NOTIFICHE_NOWRAP)
        messaggio = ("{} - {}".format(timestamp, messaggio))
        if per_not_info == "notifying":
            old_messaggio = self.get_state(persistent_notification_info, attribute="message")
            messaggio = (old_messaggio + "\n" + messaggio) if len(old_messaggio)<2500 else messaggio
        self.call_service("persistent_notification/create", notification_id = "info_messages", message = messaggio, title = "Centro Messaggi" )
