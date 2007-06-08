#!/usr/bin/env python
"""Animu Player v0.1
By: Stephan Sokolow (deitarion/SSokolow)

A minimal but pleasantly helpful PyGTK wrapper for MPlayer. You have to try it to understand how nice it is. :)

TODO:
- Add code to allow auto-skipping of intros. (default to 0:00-1:30 unless reset)
- Add an option to skip to the next episode with/without adding the current one to the list of watched things.
- Do more code clean-up.
- Figure out how the heck to set up a proper fullscreen/unfullscreen toggle using PyGTK's wonky methods and events.
	- http://www.pygtk.org/docs/pygtk/class-gtkwidget.html#signal-gtkwidget--window-state-event
	- http://www.pygtk.org/docs/pygtk/class-gdkevent.html
- Smart sorting (identify numbering order correctly even if not zero-padded)
- Figure out how to get the [stupid] gtk.AspectFrame to pick up the aspect ratio from MPlayer.
- I'm not sure what caused it, but something can cause the GUI on this to crash without taking MPlayer along.
"""

__appname__ = "Animu Player"
__appver__  = 0.1
__license__ = "GNU GPL 2 or later"

TICK_INTERVAL = 500
START_SIZE = (640, 480)
DEFAULT_ASPECT = 1.333
DEFAULT_BGCOLOR = "black"

# Note: "f" is 102 and "q" is 113 but those shouldn't be necessary.
keySyms={
		32: "SPACE",
		35: "SHARP",
		65288: "BS",
		65289: "TAB",
		65293: "ENTER",
		65307: "ESC",
		65360: "HOME",
		65361: "LEFT",
		65362: "UP",
		65363: "RIGHT",
		65364: "DOWN",
		65365: "PGUP",
		65366: "PGDWN",
		65367: "END",
		65379: "INS",
		65421: "KP_ENTER",
		65438: "KP_INS",
		65439: "KP_DEL",
		65454: "KP_DEC",
		65456: "KP0",
		65457: "KP0",
		65458: "KP1",
		65459: "KP2",
		65460: "KP3",
		65461: "KP4",
		65462: "KP5",
		65463: "KP6",
		65464: "KP7",
		65465: "KP8",
		65466: "KP9",
		65470: "F1",
		65471: "F2",
		65472: "F3",
		65473: "F4",
		65474: "F5",
		65475: "F6",
		65476: "F7",
		65477: "F8",
		65478: "F9",
		65479: "F10",
		65480: "F11",
		65481: "F12",
		65507: "CTRL",
		65535: "DEL"
		}

# Python stdlib imports
import os, signal, subprocess, sys
from optparse import OptionParser

# PyGTK imports
import pygtk
pygtk.require('2.0')
import gobject, gtk

from subprocess import Popen, PIPE

def loadMplayerInputConf():
	for path in ("~/.mplayer/input.conf", '/usr/share/mplayer/input.conf'):
		if os.path.exists(path):
			fileContents = file(os.path.expanduser(path), 'r').read()
			#TODO: Check whether it's worthwhile to optimize this.
			keys = [x.strip().split('#')[0].strip().split(' ',1) for x in fileContents.split('\n') if not x.startswith('#')]
			keys = [[y.strip() for y in x] for x in keys if len(x) == 2]			
			return dict(keys)
	return {}

class Player(object):
	def __init__(self, playlist, aspect=DEFAULT_ASPECT):
		self.playlist = playlist
		self.filename, self.filepath = "", ''
		self.child, self.fullscreen = None, False
		
		# Load the keyboard config
		self.keyConfig = loadMplayerInputConf()
	
		# Set up the window
		self.window = gtk.Window()
		self.window.set_icon_name('video')
		self.window.set_default_size(*START_SIZE)
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.set_title(__appname__)
		self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(DEFAULT_BGCOLOR))
		
		self.aspect = gtk.AspectFrame(ratio=aspect, obey_child=False)
		
		self.socket = gtk.Socket()
		self.aspect.add(self.socket)
		self.window.add(self.aspect)
		self.window.show()
		self.aspect.show()
		self.socket.show()


		# Connect the callbacks
		self.window.connect("destroy", self.cb_window_close)
		self.window.connect("key_press_event", self.cb_key_press)

		# Start playback and hook the monitor pseudo-thread
		self.cb_tick()
		gobject.timeout_add(TICK_INTERVAL, self.cb_tick)

	def kill_player():
		if not self.child.poll():
			os.kill(self.child.pid, signal.SIGTERM)
			self.child.wait()		

	def cb_window_close(self, widget, data=None):
		self.kill_player()
		gtk.main_quit()

	def cb_key_press(self, widget, event, data=None):
		#self.child.stdin.write(event.string)
		if keySyms.has_key(event.keyval):
			key = keySyms[event.keyval]
		else:
			key = event.string
			
		if self.keyConfig.has_key(key):
			action = self.keyConfig[key]
			if action.startswith('pt_step') or action.startswith('pt_up_step'):
				temp = action.split()
				if len(temp) > 1:
					changeVal = temp[1]
					pass # TODO: Go back or forward according to changeVal without marking the current thing as read.
				else:
					pass # Invalid, but we don't want to crash
			elif action == 'quit':
				self.window.destroy()
			elif action == 'vo_fullscreen':
				if self.fullscreen == False:
					self.window.fullscreen()
					self.fullscreen = True #FIXME: This doesn't track WM-based changes.
				else:
					self.window.unfullscreen()
					self.fullscreen = False #FIXME: This doesn't track WM-based changes.
			else:
				self.child.stdin.write("%s\n" % action)
		else:
			print "\rNo Binding for '%s'\n" % key

	def cb_tick(self, data=None):
		if not self.child or self.child.poll() is not None:
			# None = still running, negative = terminated by signal, positive = exit code
			if self.filename and not self.filename in get_watched_list():
				fh = file(os.path.expanduser("~/.config/animu_played"), 'a')
				fh.write('\n%s' % self.filename)
				fh.close()
			if self.playlist:
				self.filepath = os.path.abspath(os.path.normpath(self.playlist.pop(0)))
				self.filename, sockId = os.path.split(self.filepath)[1], str(self.socket.get_id())
				
				self.window.set_title(self.filename)
				self.child = Popen(["mplayer", "-slave", "-wid", sockId, self.filepath], stdin=PIPE)
			else:
				gtk.main_quit()
		return True

def get_watched_list():
	playedListFile = file(os.path.expanduser("~/.config/animu_played"), 'a+')
	return playedListFile.read().split('\n')

def get_unplayed_contents(folderPath):
	playedList = get_watched_list()
	return [os.path.join(folderPath, x) for x in sorted(os.listdir(folderPath)) if not x in playedList]

def play(entries, playAll=False, aspect=DEFAULT_ASPECT):
	if isinstance(entries, basestring):
		entries = [entries]
		
	playlist = []
	for entry in entries:
		if os.path.isdir(entry):
			if playAll:
				playlist += [os.path.join(entry, x) for x in os.listdir(entry)]
			else:
				playlist += get_unplayed_contents(entry)
		else:
			playlist.append(entry)
	
	if playlist:
		pl = Player(playlist, aspect=aspect)
		gtk.main()
	else:
		gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format="No un-watched episodes found.").run()

def getFolder():
		"""Display a GTK directory chooser. Return a path if the user clicks OK or None if they click Cancel."""
		dirPicker = gtk.FileChooserDialog("Select Series Directory", None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
		                                  (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		if dirPicker.run() == gtk.RESPONSE_ACCEPT:
			path = dirPicker.get_filename()
		else:
			path = None
		dirPicker.destroy()
		return path

if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option("-D", "--force-dir", action="store_true", dest="force_dir", default=False,
	                  help="If a given path points to a filename, handle it's parent directory instead.")
	parser.add_option("-a", "--play-all", action="store_true", dest="play_all", default=False,
	                  help="Don't skip files which have already been watched before.")
	parser.add_option("-A", "--aspect-ratio", action="store", dest="aspect_ratio", default=DEFAULT_ASPECT, metavar="RATIO",
	                  help="Set RATIO as the aspect ratio. (Default is %s) Autodetection is currently broken since gtk.Socket is too brain-damaged to listen to MPlayer." % DEFAULT_ASPECT)
	
	(opts, args) = parser.parse_args()

	if opts.force_dir:
		for pos, val in args:
			while not os.path.isdir(val):
				args[pos] = os.path.split(val)[0]
	
	if len(args):
		play(args, playAll=opts.play_all, aspect=opts.aspect_ratio)
	else:
		path = getFolder()
		if path:
			play(path, playAll=opts.play_all, aspect=opts.aspect_ratio)

