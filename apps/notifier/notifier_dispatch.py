import sys
import hassapi as hass
import helpermodule as h
import yaml
import os
from packaging import version
from dataclasses import dataclass
from typing import Any, Optional
from requests import get, HTTPError, RequestException
from zipfile import ZipFile, BadZipFile
from io import BytesIO

"""
Centro Notifiche - Dispatch Module
Args:
  Version 1.0:
  Initial Version
"""
DEFAULT_TTS_GOOGLE = "google_translate_say"
DEFAULT_TTS_GOOGLE_CLOUD = "google_cloud"
DEFAULT_NOTIFY_GOOGLE = "google_assistant"
DEFAULT_SIP_SERVER_NAME = "fritz.box:5060"
DEFAULT_REVERSO_TTS = "reversotts_say"
#
URL_PACKAGE_RELEASES = "https://api.github.com/repos/caiosweet/Package-Notification-HUB-AppDaemon/releases"
URL_ZIP = "https://github.com/caiosweet/Package-Notification-HUB-AppDaemon/archive/refs/heads/{}.zip"
PATH_PACKAGES = "packages/centro_notifiche"
PATH_BLUEPRINTS = "blueprints/automation/caiosweet"
FILE_MAIN = "hub_main.yaml"
FILE_STARTUP = "notifier_startup_configuration.yaml"
FILE_RENAME = ["hub_build_message.yml","hub_customize.yaml"]
FILE_NAMES = ["hub_main.yaml","hub_alexa.yaml","hub_google.yaml","hub_build_message.yml","hub_customize.yaml","notifier_startup_configuration.yaml"]

class ApiException(Exception):
    def __init__(self, message: str, url: str):
        message = f"{message} ({url})"
        super(ApiException, self).__init__(message)

@dataclass
class StatusResponse:
    """
    Represents the response received from the  method _do_request
    """
    version: str

class FileDownloader:
    """
    A client to check API and download zip file
    """
    def __init__(self, zip_url: str, check_url: str, destination: str):
        self.zip_url = zip_url
        self.check_url = check_url
        self.destination = destination

    def _do_request(self, url: str) -> Any:
        """
        Do the HTTP request and return the response.
        This will raise an HTTP error if response status is not OK
        """
        response = get(url)
        response.raise_for_status()
        return response

    def get_status(self):
        """
        Retrieves the version from the github API
        """
        url = self.check_url
        try:
            response = self._do_request(url)
            version = response.json()[0]["tag_name"].replace("v", "")
            return StatusResponse(version=version)
        except HTTPError as e:
            return StatusResponse(version="0.0.0")
            raise ApiException(f"error occurred while asking Github release: {e}", url) from None

    def download_extract_files(self, file_names):
        """
        Download the files from Github
        """
        url = self.zip_url
        destination = self.destination
        try:
            if isinstance(file_names, str):
                file_names = file_names.split()
            response = self._do_request(url)
            if response.status_code != 200:
                raise ApiException(f"Failed to download file. Status code: {response.status_code}", url) from None
            with ZipFile(BytesIO(response.content)) as zip_file:
                for names in file_names:
                    for zip_info in zip_file.infolist():
                        if zip_info.is_dir():
                            continue
                        index = str(zip_info.filename).find(names)
                        if index != -1:
                            zip_info.filename = str(zip_info.filename)[index:]
                            zip_file.extract(zip_info, destination)
        except RequestException as e:
            raise ApiException(f"Error occurred during file download: {e}", url) from None
        except BadZipFile as e:
            raise ApiException(f"Error occurred while extracting zip file: {e}", url) from None
        except Exception as e:
            raise ApiException(f"Error generic occurred while downloading file: {e}", url) from None

    #####################################################################


class Notifier_Dispatch(hass.Hass):
    client: Optional[FileDownloader] = None

    def initialize(self):
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
        self.config_dir = "/homeassistant" #self.config["config_dir"]
        self.log(f"configuration dir: {self.config_dir}")
        ### FROM SENSOR CONFIG
        sensor_config = self.get_state("sensor.notifier_config", attribute="all", default={})
        self.notifier_config("initialize", sensor_config.get("attributes", {}), {})  
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
        self.run_in(self.package_download, 10)

    #####################################################################
    def ad_command(self, ad):
        command = ad.get("command")
        self.log(f"Run command: {command}")
        match command:  # type: ignore
            case "restart":
                self.restart_app("Notifier_Dispatch")
            case _:
                self.log(f"The command is invalid.")

    def notifier_config(self, event_name, cfg, kwargs):
        self.log(f"-->>> CONFIG {event_name} UPTATED")
        self.cfg = cfg
        self.cfg_gh_tts = cfg.get("tts_google", DEFAULT_TTS_GOOGLE)
        self.cfg_gh_notify = cfg.get("notify_google", DEFAULT_NOTIFY_GOOGLE)
        self.cfg_phone_sip_server = cfg.get("sip_server_name", DEFAULT_SIP_SERVER_NAME)
        self.cfg_gh_tts_cloud = cfg.get("tts_google_cloud", DEFAULT_TTS_GOOGLE_CLOUD)
        self.cfg_reverso_tts = cfg.get("reverso_tts", DEFAULT_REVERSO_TTS)
        self.cfg_alexa_skill_id = cfg.get("alexa_skill_id", "")
        self.cfg_personal_assistant = cfg.get("personal_assistant", "Assistant")
        self.cfg_notify_select = cfg.get("notify_select", "notify")
        self.cfg_dnd = cfg.get("dnd", "off")
        self.cfg_location_tracker = cfg.get("location_tracker", "home")
        # self.log(f"USER INPUT CONFIG: {cfg}")
        self.log(f"-->>> END {event_name} UPTATED")

    def get_remote_version(self):  # kwargs
        try:
            status = self.client.get_status()
            return status.version
        except ValueError as ex:
            self.log(f"Invalid status response: {ex}")

    def get_zip_file(self, file_names):
        try:
            self.client.download_extract_files(file_names)
            self.log("Download started")
        except ValueError as ex:
            self.log(f"Download failed: {ex}")

    def get_local_version(self, cn_path, file_names):
        ### Get the local version ###########
        version_installed = "0.0.0"
        if os.path.isfile(cn_path + file_names):
            try:
                with open(cn_path + file_names, "r") as ymlfile:
                    load_main = yaml.load(ymlfile, Loader=yaml.BaseLoader)
                node = load_main["homeassistant"]["customize"]
                if "package.cn" in node:
                    version_installed = node["package.cn"]["version"]
                else:
                    version_installed = node["package.node_anchors"]["customize"]["version"]
            except Exception as ex:
                self.log(f"Error in configuration file: {ex}")
        return version_installed.replace("Main ", "")

    def _create_folder(self, folder) -> None:
        if not os.path.isdir(folder):
            try:
                os.mkdir(folder)
            except OSError:
                self.log(f"Creation of the directory {folder} failed")

    def _move_file(self, source_folder, destination_folder, file_name) -> None:
        try:
            os.rename(source_folder + file_name, destination_folder + file_name)
        except OSError:
            self.log(f"Move of file {file_name} failed")

    def _rename_file(self, folder, source_list, extension) -> None:
        try: 
            if isinstance(source_list, str):
                os.rename(folder+source_list, folder+source_list+extension)
            else:
                for element in source_list:
                    os.rename(folder+element, folder+element+extension)
        except OSError:
            self.log(f"Rename of the files in {source_list} failed")

    def get_path_packges(self, ha_config_file, cn_path):
        ### Find the path to the Packages folder
        config = None
        if os.path.isfile(ha_config_file):
            try:
                with open(ha_config_file, "r") as ymlfile:
                    config = yaml.load(ymlfile, Loader=yaml.BaseLoader)
                if "homeassistant" in config and "packages" in config["homeassistant"]:
                    packages_folder = config["homeassistant"]["packages"]
                    cn_path = f"{self.config_dir}/{packages_folder}/centro_notifiche/"

                    self.log(f"Package folder: {packages_folder}")
                else:
                    packages_folder = self.cfg.get("packages_folder")
                    cn_path = f"{packages_folder}/centro_notifiche/"
                    self.log(f"Package folder from user input: {packages_folder}")
                if packages_folder is None:
                    self.log(f"Package folder not foud.")
                    return
                return cn_path
            except Exception as ex:
                self.log("An error occurred in loading packages path, download abort {}".format(ex), level="ERROR")
                self.set_debug_sensor("An error occurred in loading packages path, download abort", ex)
                self.log(sys.exc_info())

    def package_download(self, delay):
        is_download = self.cfg.get("download")
        is_beta = self.cfg.get("beta_version")
        if not is_download:
            return
        ha_config_file = self.config_dir + "/configuration.yaml"
        cn_path = self.config_dir + f"/{PATH_PACKAGES}/"
        blueprints_path = self.config_dir + f"/{PATH_BLUEPRINTS}/"
        ###################################################
        branche = "beta" if is_beta else "main"
        url_main = URL_ZIP.format(branche)
        cn_path = self.get_path_packges(ha_config_file, cn_path)  ##<-- cn_path
        self.client = FileDownloader(url_main, URL_PACKAGE_RELEASES, cn_path)  # <-- START THE CLIENT
        version_latest = self.get_remote_version()  # <-- recupero versione da github
        version_installed = self.get_local_version(cn_path, FILE_MAIN)  # <-- recupero versione locale
        self.log(f"package version latest: {version_latest}")
        self.log(f"package version Installed: {version_installed}")
        ### Download if the version is older ##############
        if version.parse(version_installed) < version.parse(version_latest):
            self._create_folder(cn_path)
            self._rename_file(cn_path,FILE_RENAME,".OLD") #<-- rinomino alcuni file di interesse
            self.get_zip_file(FILE_NAMES)  # <-- scarico ZIP
            if "alexa_media" not in self.config["components"]:
                self._rename_file(cn_path,"hub_alexa.yaml",".old")
            if "cast" not in self.config["components"]:
                self._rename_file(cn_path,"hub_google.yaml",".old")
            self._create_folder(blueprints_path)
            self._move_file(cn_path, blueprints_path, FILE_STARTUP)
            ###################################################
            self.call_service("homeassistant/reload_all")
            self.restart_app("Notifier_Dispatch")
        self.log("####    PROCESS COMPLETED    ####")
        if version_installed > "4.0.1":
            self.log(f"{self.cfg.get('personal_assistant')} ready!")
        else:
            self.log(f"Please, download blueprint and configure it. When done, restart AppDaemon.")

    #####################################################################
    def set_debug_sensor(self, state, error):
        attributes = {}
        attributes["icon"] = "mdi:wrench"
        attributes["dispatch_error"] = error
        self.set_state(self.debug_sensor, state=state, attributes={**attributes})

    def createTTSdict(self, data) -> list:
        dizionario = ""
        if data == "" or (not h.check_notify(data)):
            flag = False
        elif str(data).lower() in ["1", "true", "on", "yes"]:
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
                dizionario = data if isinstance(data, dict) else eval(data)  # convert to dict
                if dizionario.get("mode") != None:
                    flag = h.check_boolean(dizionario["mode"])
                else:
                    flag = True
        return [flag, dizionario]

    def notifier(self, event_name, data, kwargs):
        self.log("#### START NOTIFIER_DISPATCH ####")
        if isinstance(data.get("ad"), dict):
            self.ad_command(data.get("ad"))
            return
        assistant_name = self.cfg_personal_assistant
        location_status = self.get_state(self.location_tracker, default=self.cfg_location_tracker)
        ### FLAG
        priority_flag = h.check_boolean(data["priority"])
        noshow_flag = h.check_boolean(data["no_show"])
        location_flag = h.check_location(data["location"], location_status)
        notify_flag = h.check_notify(data["notify"])
        ### GOOGLE ####
        google_flag = self.createTTSdict(data["google"])[0] if len(str(data["google"])) != 0 else False
        google = self.createTTSdict(data["google"])[1] if len(str(data["google"])) != 0 else False
        google_priority_flag = False
        if google_flag:
            if "priority" in google:
                if str(google.get("priority")).lower() in ["true", "on", "yes", "1"]:
                    google_priority_flag = True
        ### ALEXA ####
        alexa_flag = self.createTTSdict(data["alexa"])[0] if len(str(data["alexa"])) != 0 else False
        alexa = self.createTTSdict(data["alexa"])[1] if len(str(data["alexa"])) != 0 else False
        alexa_priority_flag = False
        if alexa_flag:
            if "priority" in alexa:
                if str(alexa.get("priority")).lower() in ["true", "on", "yes", "1"]:
                    alexa_priority_flag = True
        ### FROM BINARY ###
        dnd_status = self.get_state(self.tts_dnd, default=self.cfg_dnd)
        ### FROM INPUT BOOLEAN ###
        guest_status = self.get_state(self.guest_mode)
        priority_status = (self.get_state(self.priority_message) == "on") or priority_flag
        ### FROM SELECT ###
        notify_name = self.get_state(self.text_notify, default=self.cfg_notify_select)
        ### FROM INPUT SELECT ###
        phone_notify_name = self.get_state(self.phone_notify)
        ### NOTIFICATION ###
        if priority_status:
            useNotification = True
        elif (
            self.get_state(self.text_notifications) == "on" and data["message"] != "" and notify_flag and location_flag
        ):
            useNotification = True
        else:
            useNotification = False
        ### PERSISTENT ###
        if priority_status:
            usePersistentNotification = True
        elif self.get_state(self.screen_notifications) == "on" and data["message"] != "" and not noshow_flag:
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        ### TTS ###
        if priority_status or google_priority_flag or alexa_priority_flag:
            useTTS = True
        elif (
            self.get_state(self.speech_notifications) == "on"
            and dnd_status == "off"
            and (location_status == "home" or guest_status == "on")
        ):
            useTTS = True
        else:
            useTTS = False
        ### PHONE ###
        if priority_status:
            usePhone = True
        elif self.get_state(self.phone_notifications) == "on" and data["message"] != "" and dnd_status == "off":
            usePhone = True
        else:
            usePhone = False
        ### TTS SWITCH ###
        gh_switch = self.get_state(self.gh_switch_entity)
        alexa_switch = self.get_state(self.alexa_switch_entity)
        ### SERVIZIO TTS/NOTIFY DI GOOGLE ###
        if self.get_state(self.gh_tts_google_mode) != None:
            if self.get_state(self.gh_tts_google_mode).lower() == "reverso":
                gh_notifica = self.cfg_reverso_tts
            elif self.get_state(self.gh_tts_google_mode).lower() == "google cloud":
                gh_notifica = self.cfg_gh_tts_cloud
            elif self.get_state(self.gh_tts_google_mode).lower() == "google say":
                gh_notifica = self.cfg_gh_tts
            else:
                gh_notifica = self.cfg_gh_notify
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
                self.log("An error occurred in persistent notification: {}".format(ex), level="ERROR")
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
                self.phone_manager.send_voice_call(data, phone_notify_name, self.cfg_phone_sip_server)
            except Exception as ex:
                self.log("An error occurred in phone notification: {}".format(ex), level="ERROR")
                self.set_debug_sensor("Error in Phone Notification: ", ex)
                self.log(sys.exc_info())
        if useTTS:
            if (gh_switch == "on" or google_priority_flag) and google_flag:
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
                    if "message" not in alexa:
                        alexa["message"] = data["message"]
                    if "title" not in alexa:
                        alexa["title"] = data["title"]
                self.alexa_manager.speak(alexa, self.cfg_alexa_skill_id, self.cfg)
        ### ripristino del priority a OFF
        if self.get_state(self.priority_message) == "on":
            self.set_state(self.priority_message, state="off")
