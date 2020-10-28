import hassapi as hass
import datetime
import re

"""
Class Notification_Manager handles sending text to notfyng service
"""
__NOTIFY__ = "notify/"
SUB_NOTIFICHE = [(" +", " "), ("\s\s+", "\n")]


class Notification_Manager(hass.Hass):
    def initialize(self):
        # self.text_last_message = globals.get_arg(self.args, "text_last_message")
        self.text_last_message = self.args["text_last_message"]

    def rewrite_notify(self, data, notify_name):
        return (
            notify_name
            if (str(data).lower() in ["true", "on", "yes"] or data == "1" or data == 1 or data == "")
            else data
        )


class Notification_Manager(hass.Hass):
    def initialize(self):
        # self.text_last_message = globals.get_arg(self.args, "text_last_message")
        self.text_last_message = self.args["text_last_message"]

    def rewrite_notify(self, data, notify_name):
        return (
            notify_name
            if (str(data).lower() in ["true", "on", "yes"] or data == "1" or data == 1 or data == "")
            else data
        )

    def prepare_text(self, html, message, title, timestamp, assistant_name):
        if str(html).lower() in ["true", "on", "yes", "1"]:
            title = "<b>[{} - {}] {}</b>".format(assistant_name, timestamp, title)
        else:
            title = "*[{} - {}] {}*".format(assistant_name, timestamp, title)
        return message.replace("_", "\_"), title

    def send_notify(self, data, notify_name: str, assistant_name: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = data["title"]
        message = self.replace_regular(data["message"], SUB_NOTIFICHE)
        url = data["url"]
        _file = data["file"]
        caption = data["caption"]
        link = data["link"]
        html = data["html"]
        notify_name = self.rewrite_notify(data["notify"], notify_name)
        ### SAVE IN INPUT_TEXT.LAST_MESSAGE
        self.set_state(self.text_last_message, state=message[:245])

        if notify_name.find("telegram") != -1:
            message, title = self.prepare_text(html, message, title, timestamp, assistant_name)
            self.log("[TITLE-1]: {}".format(title), ascii_encode=False)
            if link != "":
                message = "{} {}".format(message, link)
            if caption == "":
                caption = "{}\n{}".format(title, message)
            if url != "":
                extra_data = {"photo": {"url": url, "caption": caption}}
            elif _file != "":
                extra_data = {"photo": {"file": _file, "caption": caption}}
            if url != "" or _file != "":
                self.call_service(__NOTIFY__ + notify_name, message="", data=extra_data)
            else:
                self.call_service(__NOTIFY__ + notify_name, message=message, title=title)
        elif notify_name.find("whatsapp") != -1:
            message, title = self.prepare_text(html, message, title, timestamp, assistant_name)
            message = title + " " + message
            self.call_service(__NOTIFY__ + notify_name, message=message)
        else:
            if title != "":
                title = "[{} - {}] {}".format(assistant_name, timestamp, title)
            else:
                title = "[{} - {}]".format(assistant_name, timestamp)
            self.call_service(__NOTIFY__ + notify_name, message=message, title=title)

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
