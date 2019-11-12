import appdaemon.plugins.hass.hassapi as hass
import time
import datetime
import globals
import sys
from queue import Queue
from threading import Thread
import re
"""
Class Alexa Manager handles sending text to speech messages to Alexa media players
Following features are implemented:
- Speak text to choosen media_player
- Full queue support to manage async multiple TTS commands
- Full wait to tts to finish to be able to supply a callback method
"""

__NOTIFY__ = "notify/"

class Alexa_Manager(hass.Hass):

    def initialize(self) -> None:
        self.wait_time = globals.get_arg(self.args, "wait_time")
        self.alexa_switch_push = globals.get_arg(self.args, "alexa_switch_push")
        self.alexa_tts = "alexa_media"
        self.queue = Queue(maxsize=0)
        self._when_tts_done_callback_queue = Queue()
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()
        # gruppo = self.get_state("input_select.notification_media_player_alexa", attribute="options")
        # self.set_state("group.hub_media_player_alexa", state = "on", attributes = {"entity_id": gruppo})

    def speak(self, data):
        """ Speak the provided text through the media player """
        default_restore_volume = float(self.get_state(globals.get_arg(self.args, "default_restore_volume")))/100
        wait_time = float(self.get_state(self.wait_time))
        if self.queue.qsize() == 0:
            self.volume_get(data["media_player_alexa"],default_restore_volume)
        if data["message_tts"] != "": 
            data.update({"message": data["message_tts"]})
        switch_push = self.get_state(self.alexa_switch_push)
        message = data["message"].replace("\n","").replace("   ","").replace("  "," ").replace("_"," ").replace("!",".")

        # if switch_push == "on" and (data["alexa_type"] == "push" or data["alexa_push"] == '1'):
        #     timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        # title = data["title"]
        #     if title !="":
        #         title = ("[{}] {}".format(timestamp, title))
        #     else:
        #         title = ("[{}]".format(timestamp))
        #     self.call_service(__NOTIFY__ + self.alexa_tts, data = {"type": "push"}, target = data["media_player_alexa"], message = message, title = title)
            
        """ Queues the message to be handled async, use when_tts_done_do method to supply callback when tts is done """
        self.queue.put({"switch_push": switch_push, "title": data["title"], "text": message, "volume": data["volume"], "alexa_player": data["media_player_alexa"], 
                        "alexa_type": data["alexa_type"], "wait_time": wait_time, "alexa_method": data["alexa_method"] })

    def volume_get(self, media_player, volume: float):
        self.dict_volumes = {}
        restore_volume = volume
        if 'group' in media_player:
            list_player = self.get_state(media_player, attribute="entity_id")
            self.log("MEDIA PLAYER GROUP= {}".format(list_player))
        else:
            list_player = self.converti(media_player)
            self.log("MEDIA PLAYER SINGLE: {}".format(list_player))
        for i in list_player:
            self.dict_volumes[i] = self.get_state(entity = i, attribute="volume_level") or restore_volume
            self.log("GET VOLUMES: {} - {}".format(i,self.dict_volumes[i]))
        return self.dict_volumes

    def volume_set(self, media_player, volume: float):
        if 'group' in media_player:
            entity = self.get_state(media_player, attribute="entity_id")
            self.log("SET GRUPPO MEDIA_PLAYER/VOLUME: {} / {}".format(entity,volume))
            self.call_service("media_player/volume_set", entity_id = entity, volume_level = volume)
        else:
            self.log("SET MEDIA_PLAYER/VOLUME: {} / {}".format(media_player,volume))
            self.call_service("media_player/volume_set", entity_id = media_player, volume_level = volume)

    def when_tts_done_do(self, callback:callable)->None:
        """ Callback when the queue of tts messages are done """
        self._when_tts_done_callback_queue.put(callback)

    def converti(self, stringa): 
        li = list(stringa.replace(" ", "").split(","))
        if len(li) > 1:
            self.log("SET DUMMY GROUP ALEXA")
            self.set_state("group.hub_media_player_alexa", state = "on", attributes = {"entity_id": li})
        return li

    def worker(self):
        while True:
            data = self.queue.get()
            alexa_player = data["alexa_player"]

            if self.entity_exists("group.hub_media_player_alexa") and len(self.converti(data["alexa_player"])) > 1:
                alexa_player = "group.hub_media_player_alexa"

            """ ALEXA TYPE-METHOD """

            if data["switch_push"] == "on": #and (data["alexa_type"] == "push" or data["alexa_push"] == '1'):
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                title = data["title"]
                if title !="":
                    title = ("[{}] {}".format(timestamp, title))
                else:
                    title = ("[{}]".format(timestamp))
                self.call_service(__NOTIFY__ + self.alexa_tts, data = {"type": "push"}, target = alexa_player, title = title, message = data["text"])
                time.sleep(0.5)
            
            if data["alexa_type"] != "push":
                if data["alexa_type"] == "tts":
                    alexa_data = {"type": "tts"}
                    data["wait_time"] += 2
                else:
                    data["wait_time"] += 3.5
                    alexa_data = {"type": data["alexa_type"],
                                    "method": data["alexa_method"]
                                    }

                """ ALEXA TIME-TO-SPEAK """
                chars = data["text"].count('')
                duration = ((chars * 0.00133) * 60) + data["wait_time"] 

                """ SPEAK """
                #self.log("WORKER ALEXA PLAYER = {} ".format(alexa_player))
                #self.log("| CHARS = {} | DURATION = {}".format(chars,round(duration,2)))
                self.call_service(__NOTIFY__ + self.alexa_tts, data = alexa_data, target = alexa_player, message = data["text"])
                self.volume_set(alexa_player, data["volume"])

                """ Sleep and wait for the tts to finish """
                time.sleep(duration)

            self.queue.task_done()

            if self.queue.qsize() == 0:
                self.log("QSIZE = 0 - Worker thread exiting")
                """ RESTORE VOLUME """
                if self.dict_volumes:
                    for i,j in self.dict_volumes.items():
                        self.call_service("media_player/volume_set", entity_id = i, volume_level = j)
                        self.log("VOLUME RIPROGRAMMATO: {} - {}".format(j,i))
                        # Force Set state
                        self.set_state(i, attributes = {"volume_level": j})

                # It is empty, make callbacks
                try:
                    while(self._when_tts_done_callback_queue.qsize() > 0):
                        callback_func = self._when_tts_done_callback_queue.get_nowait()
                        callback_func() # Call the callback
                        self._when_tts_done_callback_queue.task_done()
                except:
                    self.log("ERRORE NEL TRY EXCEPT", level="ERROR")
                    self.error("ERRORE NEL TRY EXCEPT", level="ERROR")
                    pass # Nothing in queue

"""
#https://github.com/python-telegram-bot/python-telegram-bot/blob/master/telegram/utils/helpers.py
def escape_markdown(text):
    #Helper function to escape telegram markup symbols.
    escape_chars = '\*_`\['
    return re.sub(r'([%s])' % escape_chars, r'\\\1', text)

String escapedMsg = toEscapeMsg
    .replace("_", "\\_")
    .replace("*", "\\*")
    .replace("[", "\\[")
    .replace("`", "\\`");

list_player = self.get_state("input_select.notification_media_player_alexa", attribute="options")

TEST
                # Restore volume
                self.call_service("media_player/volume_set", entity_id = self.args["player"], volume_level = volume)
                # Set state locally as well to avoid race condition
                self.set_state(self.args["player"], attributes = {"volume_level": volume})

                # o anche
                volume = self.get_state(<entity_name>, attribute='volume_level') or 0.50

                if 100 < chars < 150:
                    self.log("-----DURATION-2 + DUE {}:".format(duration2+2))
                    time.sleep(duration2 + 2)
                else:
                    self.log("-----DURATION-1 + 0.5 {}:".format(duration1+0.5))
                    time.sleep(duration1 + 0.5)

                #self.log("\n| DURATION     | PAROLE = {} | CHARS = {} \n| OLD = {} \n| (1) = {} \n| (2) = {} \n| (3) = {}".format(parole,chars,round(duration,2),round(duration1,2),round(duration2,2),round(duration3,2)))
                parole = len(data["text"].split()) ##+ data["text"].count('.') + data["text"].count(',') + data["text"].count('-')
                #self.log("PAROLE: {} - CHARS: {}".format(parole,chars))
                # duration = (len(data["text"].split()) / 2) + data["wait_time"]
                # duration1 = ((len(data["text"].split()) / 130) * 60) + data["wait_time"]
                # duration2 = ((parole * 0.008) * 60) + data["wait_time"]
"""                