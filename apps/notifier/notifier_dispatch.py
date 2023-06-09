import sys

import hassapi as hass
import helpermodule as h
import yaml
import os
import requests

#
# Centralizes messaging.
#
# Args:
#
# Version 1.0:
#   Initial Version

DEFAULT_TTS_GOOGLE = "google_translate_say"
DEFAULT_TTS_GOOGLE_CLOUD = "google_cloud"
DEFAULT_NOTIFY_GOOGLE = "google_assistant"
DEFAULT_SIP_SERVER_NAME = "fritz.box:5060"
DEFAULT_REVERSO_TTS = "reversotts_say"

URL_PACKAGE_RELEASES = "https://api.github.com/repos/caiosweet/Package-Notification-HUB-AppDaemon/releases"
URL_BASE_REPO = "https://raw.githubusercontent.com/caiosweet/Package-Notification-HUB-AppDaemon/{}/{}/{}"
PATH_PACKAGES = "packages/centro_notifiche"
PATH_BLUEPRINTS = "blueprints/automation/caiosweet"
FILE_MAIN = "hub_main.yaml"
FILE_ALEXA = "hub_alexa.yaml"
FILE_GOOGLE = "hub_google.yaml"
FILE_MESSAGE = "hub_build_message.yml"
FILE_STARTUP = "notifier_startup_configuration.yaml"


class Notifier_Dispatch(hass.Hass):
    def initialize(self):
        notifier_config = self.get_state("sensor.notifier_config", attribute="all", default={})
        self.cfg = notifier_config.get("attributes", {})
        self.log(f"Assistant name: {notifier_config.get('state')}")
        
        self.debug_sensor = h.get_arg(self.args, "debug_sensor")
        self.set_state(self.debug_sensor, state="off")
        self.gh_tts_google_mode = h.get_arg(self.args, "gh_tts_google_mode")
        self.gh_switch_entity = h.get_arg(self.args, "gh_switch")
        self.alexa_switch_entity = h.get_arg(self.args, "alexa_switch")

        self.tts_dnd = h.get_arg(self.args, "dnd")

        self.text_notifications = h.get_arg(self.args, "text_notifications")
        self.screen_notifications = h.get_arg(self.args, "screen_notifications")
        self.speech_notifications = h.get_arg(self.args, "speech_notifications")
        self.phone_notifications = h.get_arg(self.args, "phone_notifications")

        self.html_mode = h.get_arg(self.args, "html_mode")

        self.text_notify = h.get_arg(self.args, "text_notify")
        self.phone_notify = h.get_arg(self.args, "phone_notify")
        self.priority_message = h.get_arg(self.args, "priority_message")
        self.guest_mode = h.get_arg(self.args, "guest_mode")

        self.location_tracker = h.get_arg(self.args, "location_tracker") 
        self.phone_called_number = h.get_arg(self.args, "phone_called_number")

        #### FROM CONFIGURATION BLUEPRINT ###
        self.config = self.get_plugin_config()
        self.config_dir = self.config["config_dir"]
        self.log(f"configuration dir: {self.config_dir}")
        self.notifier_config("notifier_config", self.cfg, None) # init
        # self.log(f"configuration: {self.config}")

        ### APP MANAGER ###
        self.notification_manager = self.get_app("Notification_Manager")
        self.gh_manager = self.get_app("GH_Manager")
        self.alexa_manager = self.get_app("Alexa_Manager")
        self.phone_manager = self.get_app("Phone_Manager")
        ### LISTEN EVENT ###
        self.listen_event(self.notifier_config, "notifier_config")
        self.listen_event(self.notifier, "notifier")
        self.set_state(self.debug_sensor, state="on")
        ### DOWNLOAD MANAGER ###
        self.run_in(self.package_download, 5)

#####################################################################
    def ad_command(self, ad):
        command = ad.get('command')
        self.log(f"Run command: {command}")
        match command: # type: ignore
            case "restart":
                self.restart_app("Notifier_Dispatch")
            case _:
                self.log(f"The command is invalid.")

    def notifier_config(self, event_name, cfg, kwargs):
        self.log(f"---------- CONFIG UPTATED ----------")
        self.cfg = cfg
        self.gh_tts = cfg.get("tts_google", DEFAULT_TTS_GOOGLE)
        self.gh_notify = cfg.get("notify_google", DEFAULT_NOTIFY_GOOGLE)
        self.phone_sip_server = cfg.get("sip_server_name", DEFAULT_SIP_SERVER_NAME)
        self.gh_tts_cloud = cfg.get("tts_google_cloud", DEFAULT_TTS_GOOGLE_CLOUD)
        self.reverso_tts = cfg.get("reverso_tts", DEFAULT_REVERSO_TTS)
        self.alexa_skill_id = cfg.get("alexa_skill_id", "")

        self.cfg_personal_assistant = cfg.get("personal_assistant", "Assistant")
        self.cfg_notify_select = cfg.get("notify_select", "notify")
        self.cfg_dnd = cfg.get("dnd", "off")
        self.cfg_location_tracker = cfg.get("location_tracker", "home")
        # self.log(f"USER INPUT CONFIG: {cfg}")
        self.log(f"----------  END  UPTATED  ----------")

    def package_download(self, delay):
        ha_config = self.config_dir + "/configuration.yaml"
        cn_path = self.config_dir + f"/{PATH_PACKAGES}/"
        blueprints_path = self.config_dir + f"/{PATH_BLUEPRINTS}/"
        local_file_main = cn_path + FILE_MAIN
        version_latest = "0.0.0" # github
        version_installed = "0.0.0" # local
        is_download = self.cfg.get('download')
        is_beta = self.cfg.get('beta_version')

        # Find the path packages 
        with open(ha_config, "r") as ymlfile:
            config = yaml.load(ymlfile, Loader=yaml.BaseLoader)
        if "homeassistant" in config and "packages" in config["homeassistant"]: 
            pack_folder = config["homeassistant"]["packages"]
            cn_path = f"{self.config_dir}/{pack_folder}/centro_notifiche/"
            self.log(f"Package folder: {pack_folder}")
        else:
            pack_folder = self.cfg.get('packages_folder')
            cn_path = f"{pack_folder}/centro_notifiche/"
            self.log(f"Package folder from user input: {pack_folder}")
        if pack_folder is None:
            self.log(f"Package folder not foud.")
            return

        ### Takes the latest published version
        response = requests.get(URL_PACKAGE_RELEASES)
        version_latest = response.json()[0]["tag_name"].replace("v", "")
        self.log(f"package version latest: {version_latest}")

        ### Compare versions
        if os.path.isfile(local_file_main):
            try:
                with open(local_file_main, "r") as ymlfile:
                    load_main = yaml.load(ymlfile, Loader=yaml.BaseLoader)
                node = load_main["homeassistant"]["customize"]
                if "package.cn" in node:
                    version_installed = node["package.cn"]["version"]
                else:
                    version_installed = node["package.node_anchors"]["customize"]["version"]
            except Exception as ex:
                self.log(f"Error in configuration file: {ex}")

            version_installed = version_installed.replace("Main ", "")
        self.log(f"package version Installed: {version_installed}")

        ### Download
        if ((version_installed < version_latest) and is_download): #or version_installed < "4.0.2":
            branche = 'beta' if (is_beta or version_installed < "4.0.2") else 'main'
            url_main = URL_BASE_REPO.format(branche, PATH_PACKAGES, FILE_MAIN)
            url_alexa = URL_BASE_REPO.format(branche, PATH_PACKAGES, FILE_ALEXA)
            url_google = URL_BASE_REPO.format(branche, PATH_PACKAGES, FILE_GOOGLE)
            url_message = URL_BASE_REPO.format(branche, PATH_PACKAGES, FILE_MESSAGE)
            url_startup = URL_BASE_REPO.format(branche, PATH_BLUEPRINTS, FILE_STARTUP)

            if not os.path.isdir(cn_path):
                try:
                    os.mkdir(cn_path)
                except OSError:
                    self.log(f"Creation of the directory {cn_path} failed")
            self.request_and_save(url_main, cn_path, FILE_MAIN)

            # if not os.path.isdir(blueprints_path):
            #     try:
            #         os.mkdir(blueprints_path)
            #     except OSError:
            #         self.log(f"Creation of the directory {blueprints_path} failed")
            # self.request_and_save(url_startup, blueprints_path, FILE_STARTUP)


            if not os.path.isfile(cn_path + FILE_MESSAGE):
                self.request_and_save(url_message, cn_path, FILE_MESSAGE)
            if "alexa_media" in self.config["components"]:
                self.request_and_save(url_alexa, cn_path, FILE_ALEXA)
            if "cast" in self.config["components"]:
                self.request_and_save(url_google, cn_path, FILE_GOOGLE)
                
            self.call_service("homeassistant/reload_all")
            self.restart_app("Notifier_Dispatch")
            # self.call_service("app/restart", app="Notifier_Dispatch", namespace="appdaemon")

        self.log("####    PROCESS COMPLETED    ####")
        if version_installed != "0.0.0":
            self.log(f"{self.cfg.get('personal_assistant')} ready!")
        else:
            self.log(f"Please, download blueprint and configure it")

    def request_and_save(self, url, path, file):
        ### TODO async? run_in_executor() request downloaded mltiple file
        if os.path.isfile(path + file):
            old = path + file
            new = old.replace('.yaml', '.OLD')
            os.rename(old, new)

        self.log(f"download {file} start!")
        response = requests.get(url)
        open(path + file, "wb").write(response.content)
        self.log(f"download {file} complete!")

#####################################################################
    def set_debug_sensor(self, state, error):
        attributes = {}
        attributes["icon"] = "mdi:wrench"
        attributes["dispatch_error"] = error
        self.set_state(self.debug_sensor, state=state, attributes={**attributes})
    
    def createTTSdict(self,data) -> list:
        dizionario = ""
        if data == "" or (not h.check_notify(data)):
            flag = False
        elif str(data).lower() in ["1","true","on","yes"]:
            flag = True
            dizionario = {}
        else:
            if "OrderedDict([(" in str(data):
                dizionario = h.convert(list(data.split("'")))
                if dizionario.get("mode") != None:
                    flag = h.check_boolean(dizionario["mode"])
                else:
                    flag = True
            else:
                dizionario = data if isinstance(data, dict) else eval(data) # convert to dict
                if dizionario.get("mode") != None:
                    flag = h.check_boolean(dizionario["mode"])
                else:
                    flag = True
        return [flag,dizionario]

    def notifier(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")
        if isinstance(data.get("ad"), dict):
            self.ad_command(data.get("ad"))
            return

        assistant_name = self.cfg_personal_assistant #Maybe BUG
        location_status = self.get_state(self.location_tracker, default=self.cfg_location_tracker) #1st BUG reload group
        ### FLAG
        priority_flag = h.check_boolean(data["priority"])
        noshow_flag = h.check_boolean(data["no_show"])
        location_flag = h.check_location(data["location"],location_status)
        notify_flag = h.check_notify(data["notify"])
        ### GOOGLE ####
        google_flag = self.createTTSdict(data["google"])[0] if len(str(data["google"])) != 0 else False
        google = self.createTTSdict(data["google"])[1] if len(str(data["google"])) != 0 else False
        google_priority_flag = False
        if google_flag:
          if "priority" in google:
            if str(google.get("priority")).lower() in ["true","on","yes","1"]:
                google_priority_flag = True
        ### ALEXA ####
        alexa_flag = self.createTTSdict(data["alexa"])[0] if len(str(data["alexa"])) != 0 else False
        alexa = self.createTTSdict(data["alexa"])[1] if len(str(data["alexa"])) != 0 else False
        alexa_priority_flag = False
        if alexa_flag:
          if "priority" in alexa:
            if str(alexa.get("priority")).lower() in ["true","on","yes","1"]:
                alexa_priority_flag = True
        ### FROM BINARY ###
        dnd_status = self.get_state(self.tts_dnd, default=self.cfg_dnd) #2nd BUG reload template
        ### FROM INPUT BOOLEAN ###
        guest_status = self.get_state(self.guest_mode)
        priority_status = (self.get_state(self.priority_message) == "on") or priority_flag
        ### FROM SELECT ###
        notify_name = self.get_state(self.text_notify, default=self.cfg_notify_select) #3nd BUG reload template
        ### FROM INPUT SELECT ###
        phone_notify_name = self.get_state(self.phone_notify)
        ### NOTIFICATION ###
        if priority_status:
            useNotification = True
        elif self.get_state(self.text_notifications) == "on" and  data["message"] !="" and notify_flag and location_flag:
            useNotification = True
        else:
            useNotification = False
        ### PERSISTENT ###
        if priority_status:
            usePersistentNotification = True
        elif self.get_state(self.screen_notifications) == "on" and data["message"] !="" and not noshow_flag:
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        ### TTS ###
        if priority_status or google_priority_flag or alexa_priority_flag:
            useTTS = True
        elif self.get_state(self.speech_notifications) == "on" and dnd_status == "off" and (location_status == "home" or guest_status == "on"):
            useTTS = True
        else:
            useTTS = False
        ### PHONE ###
        if priority_status:
            usePhone = True
        elif self.get_state(self.phone_notifications) == "on" and data["message"] !="" and dnd_status == "off":
            usePhone = True
        else:
            usePhone = False
        ### TTS SWITCH ###
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        ### SERVIZIO TTS/NOTIFY DI GOOGLE ###
        if self.get_state(self.gh_tts_google_mode) != None:
            if self.get_state(self.gh_tts_google_mode).lower() == "reverso":
                gh_notifica = self.reverso_tts
            elif self.get_state(self.gh_tts_google_mode).lower() == "google cloud":
                gh_notifica = self.gh_tts_cloud
            elif self.get_state(self.gh_tts_google_mode).lower() == "google say":
                gh_notifica = self.gh_tts
            else: 
                gh_notifica = self.gh_notify
        ### FROM SCRIPT_NOTIFY ###
        if data["called_number"] == "":
            data.update({"called_number": self.get_state(self.phone_called_number)})
        if data["html"] == "":
            data.update({"html": self.get_state(self.html_mode)})
        ###########################
        self.set_state(self.debug_sensor, state="OK")
        ###########################
        if usePersistentNotification:
            try:
                self.notification_manager.send_persistent(data, assistant_name)
            except Exception as ex:
                self.log("An error occurred in persistent notification: {}".format(ex),level="ERROR")
                self.set_debug_sensor("Error in Persistent Notification: ", ex)
                self.log(sys.exc_info()) 
        if useNotification:
            try:
                self.notification_manager.send_notify(data, notify_name, assistant_name)
            except Exception as ex:
                self.log("An error occurred in text notification: {}".format(ex), level="ERROR")
                self.set_debug_sensor("Error in Text Notification: ", ex)
                self.log(sys.exc_info())
        if usePhone:
            try:
                self.phone_manager.send_voice_call(data, phone_notify_name, self.phone_sip_server)
            except Exception as ex:
                self.log("An error occurred in phone notification: {}".format(ex),level="ERROR")
                self.set_debug_sensor("Error in Phone Notification: ", ex)
                self.log(sys.exc_info())
        if useTTS:
            if  (gh_switch == "on" or google_priority_flag) and google_flag:
                if (data["google"]) != "":
                    if "message" not in google:
                        google["message"] = data["message"]
                    if "media_content_id" not in google:
                        google["media_content_id"] = ""
                    if "media_content_type" not in google:
                        google["media_content_type"] = ""
                self.gh_manager.speak(google, self.get_state(self.gh_tts_google_mode), gh_notifica, self.cfg)
            if (alexa_switch == "on" or alexa_priority_flag) and alexa_flag:
                if (data["alexa"]) != "":
                    if  "message" not in alexa:
                        alexa["message"] = data["message"]
                    if  "title" not in alexa:
                        alexa["title"] = data["title"]
                self.alexa_manager.speak(alexa, self.alexa_skill_id, self.cfg)
        ### ripristino del priority a OFF
        if (self.get_state(self.priority_message) == "on"):
            self.set_state(self.priority_message, state = "off")
