#!/usr/bin/python

import string

import pygtk
pygtk.require('2.0')
import gtk,sys

# Set up the window
window = gtk.Window()
window.set_default_size(640,480)
window.show()

socket = gtk.Socket()
socket.show()
window.add(socket)

print "Socket ID=", socket.get_id()
window.connect("destroy", gtk.mainquit)

def cb_key_press(widget, event, data):
    print event #TODO: Hand the data off to the child MPlayer process.

def plugged_event(widget):
    print "I (",widget,") have just had a plug inserted!" 

socket.connect("plug-added", plugged_event)
window.connect("key_press_event", cb_key_press)

if len(sys.argv) == 2:
    socket.add_id(long(sys.argv[1]))

gtk.main()
