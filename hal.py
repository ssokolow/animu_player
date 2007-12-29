"""A simplified HAL wrapper using dbus-python for checking for removable devices."""

import dbus, os, subprocess, time
bus = dbus.SystemBus()

hal_manager = bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')

def getProps(udi, props):
	"""A convenience wrapper for retrieving a list of properties for a given udi.
	
	TODO: Plan for possible exceptions. (eg. the HAL KeyError equivalent)
	"""
	if isinstance(props, basestring):
		props = [props]
	obj = bus.get_object('org.freedesktop.Hal', udi)
	temp = [(prop, obj.GetProperty(prop, dbus_interface='org.freedesktop.Hal.Device')) for prop in props]
	if len(temp) == 1:
		return temp[0][1]
	else:
		return dict(temp)

def getMountableRemovables():
	"""Return a dict of relevant tuples for displaying a list of removable 
	media which is or can be mounted."""
	results = {}
	wanted_keys = ['volume.is_mounted', 'volume.mount_point', 'storage.drive_type', 'volume.disc.type', 'volume.label']
	volume_udi_list = hal_manager.FindDeviceByCapability('volume', dbus_interface='org.freedesktop.Hal.Manager')

	for udi in volume_udi_list:
		props = getProps( udi, ('volume.mount_point', 'block.storage_device', 'volume.is_mounted', 'volume.label'))
		props.update(getProps( props['block.storage_device'], ('storage.drive_type', 'storage.removable')))

		if not (props['storage.removable'] and getProps( props['block.storage_device'], 'storage.removable.media_available') and getProps( udi, 'volume.fstype')):
			continue # We only want removable media containing a mountable filesystem.

		props['volume.disc.type'] = (props['storage.drive_type'] == 'cdrom') and getProps( udi, 'volume.disc.type') or ''
		
		results[udi] = dict([(x, props[x]) for x in props if x in wanted_keys])
	return results

def mountUdi(udi):
	props = getProps(udi, ['volume.is_mounted', 'volume.fstype', 'volume.label', 'block.device'])
	
	if props['volume.is_mounted']:
		return True # Already mounted.
	elif not props['volume.fstype']:
		return False # Blank CD/DVD or possibly an unformatted medium.
	
	try:
		# Try to mount using HAL.
		mountPoint = props['volume.label'].replace('/','_') or ('volume-%s' % time.time())
		obj = bus.get_object('org.freedesktop.Hal', udi)
		obj.Mount(mountPoint, props['volume.fstype'], '', dbus_interface='org.freedesktop.Hal.Device.Volume')
	except dbus.DBusException, err:
		if not 'org.freedesktop.Hal.Device.Volume.PermissionDenied' in err.message:
			raise #TODO: Check for the HAL exception properly.
		
		try:
			# Fall back to calling the mount command for things in fstab.
			# TODO: Check if there's a HAL way to do this. 
			subprocess.check_call(['mount', props['block.device']])
		except subprocess.CalledProcessError:
			return False
	return True

def unmountUdi(udi):
	props = getProps(udi, ['volume.is_mounted', 'block.device'])
	
	if not props['volume.is_mounted']:
		return True # Obviously we can't unmount what isn't mounted in the first place.
	
	try:
		obj = bus.get_object('org.freedesktop.Hal', udi)
		obj.Unmount('', dbus_interface='org.freedesktop.Hal.Device.Volume')
	except dbus.DBusException, err:
		if not 'org.freedesktop.Hal.Device.Volume.NotMountedByHal' in err.message:
			raise #TODO: Check for the HAL exception properly.
		
		try:
			# Fall back to calling the umount command for things in fstab.
			# TODO: Check if there's a HAL way to do this. 
			subprocess.check_call(['umount', props['block.device']])
		except subprocess.CalledProcessError:
			return False
	return True
	

if __name__ == '__main__':
	results = getMountableRemovables()
	
	# For each drive...
	for udi in sorted(results):
		# Show the information getMountableRemovables() returns...
		print "udi: %s" % udi
		for item in sorted(results[udi]):
			print "%s: %s" % (item, results[udi][item])
		print

		#...and demonstrate mounting and unmounting.
		if mountUdi(udi):
			print os.listdir(getProps(udi, 'volume.mount_point'))
			if not results[udi]['volume.is_mounted']: # Only unmount if we mounted it.
				print "Unmount Status: %s" % unmountUdi(udi)

