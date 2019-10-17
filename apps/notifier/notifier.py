import appdaemon.plugins.hass.hassapi as hass
import datetime
import globals
import time
#import sys
from queue import Queue
from threading import Thread, Event
#from threading import Event
#
# Centralizes messaging. Use Google Home  Telegram and Persisten Notification
#
# Args:
#
#
# Version 1.0:
#   Initial Version

__NOTIFY__ = "notify/"
__WAIT_TIME__ = 3  # seconds
__TTS__ = "tts/"

class Notifier(hass.Hass):

    def initialize(self):
        self.gh_tts_google_mode = globals.get_arg(self.args, "gh_tts_google_mode")
        self.gh_switch_entity = globals.get_arg(self.args, "gh_switch")
        self.gh_selected_media_player = globals.get_arg(self.args, "gh_selected_media_player")

        self.alexa_tts_alexa_type = globals.get_arg(self.args, "alexa_tts_alexa_type")
        self.alexa_switch_entity = globals.get_arg(self.args, "alexa_switch")
        self.alexa_selected_media_player = globals.get_arg(self.args, "alexa_selected_media_player")

        self.tts_language = globals.get_arg(self.args, "tts_language")
        self.tts_period_of_day_volume = globals.get_arg(self.args, "tts_period_of_day_volume")

        self.text_notifications = globals.get_arg(self.args, "text_notifications")
        self.screen_notifications = globals.get_arg(self.args, "screen_notifications")
        self.speech_notifications = globals.get_arg(self.args, "speech_notifications")

        self.default_notify = globals.get_arg(self.args, "default_notify")
        self.priority_message = globals.get_arg(self.args, "priority_message")
        self.guest_mode = globals.get_arg(self.args, "guest_mode")
        self.last_message = globals.get_arg(self.args, "last_message")
        self.personal_assistant_name = globals.get_arg(self.args, "personal_assistant_name") 
        self.intercom_message_hub = globals.get_arg(self.args, "intercom_message_hub")

        self.gh_tts = "google_translate_say"
        self.alexa_tts = "alexa_media"

        # Create Queue
        self.queue = Queue(maxsize=0)
        # Create worker thread
        t = Thread(target=self.worker)
        t.daemon = True
        t.start()
        self.event = Event()
        #self.log("Thread Alive {}, {}" .format (t.isAlive(), t.is_alive()))

        self.listen_event(self.notify_hub, "hub")

    #@property
    def volume(self, entity):
        """Retrieve the audio player's volume."""
        """ First turn on Google Home mini"""
        self.log("STATO MEDIA_PLAYER: {}".format(self.get_state(entity)))
        if (self.get_state(entity) == "off" and self.gh_switch == "on"):
            self.log("accendo il GH: {}".format(entity))
            self.call_service("media_player/turn_on", entity_id = entity)
        return round(float(self.get_state(entity = entity, attribute='volume_level') or 0.2),2)

    def volume_set(self, entity, volume):
        self.log("MEDIA_PLAYER: {}".format(entity))
        self.call_service("media_player/volume_set", entity_id = entity, volume_level = float(volume))

    def notify_hub(self, event_name, data, kwargs):
        self.log("################## START NOTIFIER ####################")
        if self.get_state(self.text_notifications) == 'on':
            useNotification = True
            notify_name = self.get_state(self.default_notify).lower().replace(' ', '_')
        if self.get_state(self.screen_notifications) == 'on':
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        if self.get_state(self.speech_notifications) == 'on':
            useTTS = True
        else:
            useTTS = False

        self.gh_switch = self.get_state(self.gh_switch_entity )
        self.alexa_switch = self.get_state(self.alexa_switch_entity)
        self.alexa_tts_type = str(self.get_state(self.alexa_tts_alexa_type)).lower()
        #self.log(data['message'])
        #self.log(data['title'])
        #self.log(notify_name)

        if data['media_player_google'] == '':
            data.update({'media_player_google': self.get_state(self.gh_selected_media_player)})
        if data['media_player_alexa'] == '':
           data.update({'media_player_alexa': self.get_state(self.alexa_selected_media_player)})
        if data['volume'] == '':
            data.update({'volume': self.get_state(self.tts_period_of_day_volume)})

        self.notify(notify_name, data, useTTS, useNotification, usePersistentNotification)

    def notify(self, notify_name, data, useTTS, useNotification, usePersistentNotification):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        title = data['title']
        message = data['message']
        url = data['url']
        _file = data['file']
        caption = data ['caption']

        if useNotification:
            self.log("Notifying via Telegram")
            if title !='':
                title = ("*[{} - {}]* - {}".format(self.get_state(self.personal_assistant_name), timestamp, title))
            else:
                title = ("*[{} - {}]*".format(self.get_state(self.personal_assistant_name), timestamp))
            
            if caption == '':
                caption = 'Photo'
            #self.log("TITLE - {}".format(title))
            #self.log("MESSAGE - {}".format(message))
            #self.log("URL - {}".format(url))
            #self.log("FILE - {}".format(_file))
            #self.log("CAPTION - {}".format(caption))
            if url !='':
                extra_data = { 'photo': 
                                {'url': url,
                                'caption': caption}
                            }
            elif _file !='':
                extra_data = { 'photo': 
                                {'file': _file,
                                'caption': caption}
                            }
            if url !='' or _file !='':
                self.call_service(__NOTIFY__ + notify_name, 
                                message = message, 
                                title = title,
                                data = extra_data)
            else:                    
                self.call_service(__NOTIFY__ + notify_name, 
                                message = message, 
                                title = title)

        if usePersistentNotification:
            self.log("Notifying via Persistent Notification")
            self.call_service("persistent_notification/create",
                            notification_id = "info_messages",
                            message = ("{} - {}".format(timestamp, message)),
                            title = "Centro Messaggi")
        if useTTS:
            self.log("Notifying via TTS")
            #length = round(len(message)/9)
            length = round(len(message.split()) / 2) + __WAIT_TIME__
            self.queue.put({"type": "tts", "text": message, "length": length, "volume": data['volume'], 
                            "gh_player": data['media_player_google'], "alexa_player": data['media_player_alexa']})
            
            # LOGGING
            #self.log("Message added to queue. Queue is empty? {}".format(self.queue.empty()))
            self.log("Queue Size is now {}".format(self.queue.qsize()))
            self.log(self.queue.queue)

    def worker(self):
        active = True
        while active:
            try:
                # Get data from queue
                data = self.queue.get()
                if data["type"] == "terminate":
                    active = False
                else:
                    # Save current volume
                    volume_saved_gh = self.volume(data['gh_player'])
                    volume_saved_alexa = self.volume(data['alexa_player'])
                    self.log("VOLUME SALVATO: {}".format(volume_saved_gh))
                    self.log("VOLUME DESIDERATO: {}".format(data['volume']))
                    # Set to the desired volume
                    self.volume_set(data['gh_player'], data['volume'])
                    self.volume_set(data['alexa_player'], data['volume'])
                    # Alexa tts type
                    if self.alexa_tts_type == "tts":
                       alexa_tts = {'type': 'tts'}
                    elif  self.alexa_tts_type =="announce":
                       alexa_tts = {'type':'announce', 'method':'speak'}
                    else:
                       alexa_tts = {'type':'push'}
                    
                    if (data["type"] == "tts" and self.gh_switch == "on"):
                        self.call_service(__TTS__ + self.gh_tts, entity_id = data['gh_player'], message = data['text'])
                    if (data["type"] == "tts" and self.alexa_switch == "on"):
                        self.call_service(__NOTIFY__ + self.alexa_tts, target = data['alexa_player'], data = alexa_tts, message = data['text'])
                    #if (data["type"] == "tts" and self.gh_switch == "on" and self.alexa_switch == "off"):
                    #    self.call_service(__TTS__ + self.gh_tts, entity_id = data['gh_player'], message = data["text"])
                    #elif (data["type"] == "tts" and self.gh_switch == "off" and self.alexa_switch == "on"):
                    #    self.call_service(__NOTIFY__ + self.alexa_tts, data=alexa_tts, target = data['alexa_player'], message = data["text"])
                    #elif (data["type"] == "tts" and self.gh_switch == "off" and self.alexa_switch == "off"):
                    #    self.call_service(__TTS__ + self.gh_tts, entity_id = data['gh_player'], message = data["text"])
                    #    self.call_service(__NOTIFY__ + self.alexa_tts, data=alexa_tts, target = data['alexa_player'], message = data["text"])

                    # Sleep to allow message to complete before restoring volume
                    time.sleep(int(data["length"]))
                    # Restore volume
                    self.call_service("media_player/volume_set", entity_id = data['gh_player'], volume_level = volume_saved_gh)
                    self.call_service("media_player/volume_set", entity_id = data['alexa_player'], volume_level = volume_saved_alexa)
                    # Set state locally as well to avoid race condition
                    self.set_state(data['gh_player'], attributes = {"volume_level": volume_saved_gh})
            except:
                self.log("Error in worker")
                #self.log(sys.exc_info()) 
        # Rinse and repeat
        self.queue.task_done()
        self.log("Worker thread exiting")
        self.event.set()

    def terminate(self):
        self.event.clear()
        self.queue.put({"type": "terminate"})
        self.log("Terminate function called")
        self.event.wait()