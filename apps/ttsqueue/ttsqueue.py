import appdaemon.plugins.hass.hassapi as hass
from queue import Queue
from threading import Thread
from threading import Event
import time
import globals
import sys

#
# App to manage announcements via TTS and stream sound files to Google Home
#
# Provides methods to enqueue TTS and Media file requests and make sure that only one is executed at a time
# Volume of the media player is set to a specified level and then restored afterwards
#
# Args:
#
# player: media player to use for announcements
# TTSVolume: media played volume 0-1

class TTSqueue(hass.Hass):

  def initialize(self):
    
    self.log("#### TTS ####")
    self.gh_selected_media_player = globals.get_arg(self.args, "gh_selected_media_player")
    self.gh_player = self.get_state(self.gh_selected_media_player)
    self.volumeTTS = 0.4
    
    # Create Queue
    self.queue = Queue(maxsize=0)

    # Create worker thread
    t = Thread(target=self.worker)
    t.daemon = True
    t.start()
    self.event = Event()
    self.log("Thread Alive {}, {}" .format (t.isAlive(), t.is_alive()))

    self.listen_event(self.tts, "hub")

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
          #volume_saved = self.get_state(self.gh_selected_media_player, attribute="volume_level")
          
          # Turn on Google and Set to the desired volume
          #self.call_service("media_player/turn_on", entity_id = self.gh_player)
          self.call_service("media_player/volume_set", entity_id = self.gh_player, volume_level = self.volumeTTS)
          self.log("Set the Volume to {}".format(self.volumeTTS))
          
          if data["type"] == "tts":
            # Call TTS service
            self.call_service("tts/google_translate_say", entity_id = self.gh_player, message = data["text"])
            self.log("This is the text said - {}".format(data["text"]))
          
          # Sleep to allow message to complete before restoring volume
          time.sleep(int(data["length"]))
          
          # Restore volume
          #self.call_service("media_player/volume_set", entity_id = self.gh_player, volume_level = volume_saved)
          
          # Set state locally as well to avoid race condition
          #self.set_state(self.gh_player, attributes = {"volume_level": volume_saved})

      except:
        self.log("Error")
        self.log(sys.exc_info()) 

      # Rinse and repeat
      self.queue.task_done()
      
    self.log("Worker thread exiting")
    self.event.set()
       
  def tts(self, event_name, data, kwargs):
    text = data['message']
    length = len(text)/6
    self.queue.put({"type": "tts", "text": text, "length": length})
    self.log("Message added to queue. Queue empty? {}".format(self.queue.empty()))
    self.log("Queue Size is now {}".format(self.queue.qsize()))
    self.log(self.queue.queue)
    
  def terminate(self):
    self.event.clear()
    self.queue.put({"type": "terminate"})
    self.log(" Terminate function called")
    self.event.wait()
