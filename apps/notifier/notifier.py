import appdaemon.plugins.hass.hassapi as hass
import datetime
import globals

#
# Centralizes messaging. Use Google Home  Telegram and Persisten Notification
#
# Args:
#
#
# Version 1.0:
#   Initial Version

__NOTIFY__ = "notify/"
__WAIT_TIME__ = 5  # seconds

class Notifier(hass.Hass):

    @property
    def volume(self) -> float:
        """Retrieve the audio player's volume."""
        return float(self.get_state(self.gh_selected_media_player_google, attribute='volume_level') or 0.3)

    @volume.setter 
    def volume(self, value: float) -> None:
        """Turn on Google Home mini"""
        self.call_service(
            "media_player/turn_on", 
            entity_id = self.gh_player
        )

        """Set the audio player's volume."""
        self.call_service(
            "media_player/volume_set",
            entity_id = self.gh_player,
            volume_level = value
        )

    def initialize(self):
        self.timer_handle_list = []

        self.gh_tts_google_mode = globals.get_arg(self.args, "gh_tts_google_mode")
        self.gh_volume_storage = globals.get_arg(self.args, "gh_volume_storage")
        self.gh_switch = globals.get_arg(self.args, "gh_switch")
        self.gh_selected_media_player_google = globals.get_arg(self.args, "gh_selected_media_player_google")
        self.gh_language = globals.get_arg(self.args, "gh_language")
        self.gh_period_of_day_volume = globals.get_arg(self.args, "gh_period_of_day_volume")

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
        self.last_gh_notification_time = None
        self.listen_event(self.notify_hub, "hub")

    def notify_hub(self, event_name, data, kwargs):
        self.log(event_name)
        self.log(data)
        self.log(kwargs)

        if self.get_state(self.text_notifications) == 'on':
            useNotification = True
            notify_name = self.get_state(self.default_notify).lower().replace(' ', '_')
        if self.get_state(self.screen_notifications) == 'on':
            usePersistentNotification = True
        else:
            usePersistentNotification = False
        if self.get_state(self.speech_notifications) == 'on':
            useGH = True
        else:
            useGH = False
        
        self.gh_volume = self.get_state(self.gh_period_of_day_volume)
        self.gh_player = self.get_state(self.gh_selected_media_player_google)

        self.log(data['message'])
        self.log(data['title'])
        self.log(notify_name)
        self.log(self.gh_volume)
        self.log(self.gh_player)

        self.notify(notify_name, data, useGH, useNotification, usePersistentNotification)


    def notify(self, notify_name, data, useGH, useNotification, usePersistentNotification):
        timestamp = datetime.datetime.now().strftime('%H:%M')
        title = data['title']
        message = data['message']
        url = data['url']
        _file = data['file']
        caption = data ['caption']
        delay_tts = int(len(message.split()) / 2)+3

        if useNotification:
            self.log("Notifying via Telegram")
            if title !='':
                title = ("*[{} - {}]* - {}".format(self.get_state(self.personal_assistant_name), timestamp, title))
            else:
                title = ("*[{} - {}]*".format(self.get_state(self.personal_assistant_name), timestamp))
            
            if caption == '':
                caption = 'Photo'
            
            self.log("TITLE - {}".format(title))
            self.log("MESSAGE - {}".format(message))
            self.log("URL - {}".format(url))
            self.log("FILE - {}".format(_file))
            self.log("CAPTION - {}".format(caption))

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
                self.log("Sending data: " + _file + " " + url + " " + caption)

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

        if useGH:
            self.log("Notifying via Google Home")

            # Save current volume
            volume_saved = self.volume

            # LOGGING
            self.log("GH PLAYER: {}".format(self.gh_player))
            self.log("VOLUME GH DA IMPOSTARE: {}".format(self.gh_volume))
            self.log("VOLUME SALVATO {}".format(volume_saved))

            # check last message
            if self.last_gh_notification_time is not None and (
                datetime.datetime.now() - self.last_gh_notification_time
                < datetime.timedelta(seconds=__WAIT_TIME__) 
                ):
                self.timer_handle_list.append(self.run_in(self.notify_callback, __WAIT_TIME__, message=message))
            else:
                self.last_gh_notification_time = datetime.datetime.now()
                self.call_service(
                    "tts/" + self.gh_tts,
                    entity_id=self.gh_player,
                    message=message
                )

            # Restore volume
            self.run_in(self.volume_callback, delay_tts, volume_level=volume_saved)


    def notify_callback(self, kwargs):
        self.last_gh_notification_time = datetime.datetime.now()
        self.call_service(
            "tts/" + self.gh_tts,
            entity_id = self.gh_player,
            message = kwargs["message"]
        )
    
    def volume_callback (self, kwargs):
        self.call_service(
            "media_player/volume_set", 
            entity_id = self.gh_player,
            volume_level = kwargs["volume_level"]
        )
        self.log("Restore Volume")


    def terminate(self):
        for timer_handle in self.timer_handle_list:
            self.cancel_timer(timer_handle)
