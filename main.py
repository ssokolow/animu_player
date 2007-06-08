#!/usr/bin/python
"""
TODO:
- Use window.set_title() to set the Window title to the filename of the video being played.

"""

TICK_INTERVAL = 300
START_SIZE = (640, 480)

# Python stdlib imports
import os, signal, subprocess, sys

# PyGTK imports
import pygtk
pygtk.require('2.0')
import gobject, gtk

from subprocess import Popen, PIPE

class Player(object):
	def __init__(self, playlist):
		self.playlist = playlist
		self.filepath, self.child = '', None
	
		# Set up the window
		self.window = gtk.Window()
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.set_default_size(*START_SIZE)
		self.window.set_icon_name('video')
		self.window.show()

		# Set up the XEmbed socket
		self.socket = gtk.Socket()
		self.window.add(self.socket)
		self.socket.show()

		# Connect the callbacks
		self.window.connect("destroy", self.cb_window_close)
		self.window.connect("key_press_event", self.cb_key_press)

		# Start playback and hook the monitor pseudo-thread
		self.cb_tick()
		gobject.timeout_add(TICK_INTERVAL, self.cb_tick)

	def cb_window_close(self, widget, data=None):
		if not self.child.poll():
			os.kill(self.child.pid, signal.SIGTERM)
		gtk.main_quit()

	def cb_key_press(self, widget, event, data=None):
		self.child.stdin.write(event.string)

	def cb_tick(self, data=None):
		if not self.child or self.child.poll() is not None:
			# None = still running, negative = terminated by signal, positive = exit code
			if self.playlist:
				self.filepath, sockId = os.path.abspath(self.playlist.pop(0)), str(self.socket.get_id())
				self.window.set_title(os.path.split(self.filepath)[1])
				self.child = Popen(["mplayer", "-wid", sockId, self.filepath], stdin=PIPE)
			else:
				gtk.main_quit()
		return True

# Start the playing
if len(sys.argv) >= 2:
	pl = Player(sys.argv[1:])
	gtk.main()
else:
	print "ERR: No files specified"
