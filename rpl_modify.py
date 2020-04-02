#!/usr/bin/env python

"""
rpl_modify is intended to run as a standalone script. 

Here's what it does:

1. It takes up to 3 parameters (prefix, action, and optional uplink)
2. Updates its internal representation of system state (stored in state.json file)
3. Based on current system state generates RPL prefix-set
4. Pushes the RPL prefix-set to devices specified in inventory file (inventory.json) using NETCONF

"""

__author__ = "Marcin Kurek"
__version__ = "0.1"
__maintainer__ = "Marcin Kurek"
__email__ = "m.kurek@3s.pl"
__status__ = "Development"

import json
import getopt
import sys
import logging
import time
import os.path

from jinja2 import Template
from ncclient import manager

def load_inventory():
	"""
	Load inventory from file. Inventory contains metadata of all BGP sessions we are going to modify.
    
	Parameters:
	none

	Returns: 
	dict: inventory
	
	"""
	
	try:
		with open("inventory.json", encoding="utf-8") as f:
			input = json.load(f)
		return input
	except (OSError, IOError) as e:
		print(e)
		sys.exit(1)

def read_state():

    """
    Reads state from a file.
	State is a current representation of the system, i.e. which prefixes should be advertised.

    """
    with open("state.json", encoding="utf-8") as f:
        input = json.load(f)
    return input

def write_state(state:json):

    """
    Writes state to a file.

    :param state:
    :return:
    """

    with open("state.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(state, indent=4, sort_keys=True))

def update_state(prefix: str, action:str) -> str:

    logging.debug('Updating state for %s : %s', prefix, action)
    current_state = read_state()
    current_state[prefix] = action
    write_state(current_state)
    
    return current_state

def deploy(rpl_config:str, device:str):

    """
    Deploys a RPL snippet to a device.

    :param rpl_config:
    :return:
    """
    with manager.connect(host=device, port=830, username="cisco", password="cisco", device_params={'name': 'iosxr'}, hostkey_verify=False, allow_agent=False, look_for_keys=False) as nc_conn_1:
        nc_reply_1 = nc_conn_1.edit_config(target="candidate", config=rpl_config)
        nc_reply_1 = nc_conn_1.commit()
        #  nc_config = nc_conn.get(('subtree', ncc_filter))

def generate_rpl(upstream:str, current_state:dict, template_path:str):

    """
    Generates a RPL snippet based on current system state.
    :param upstream:
    :param current_state:
    :return:
    """

    src = []
    for k,v in current_state.items():
        if v == '1':
            src.append(k)
    with open(template_path, 'r', encoding='utf-8') as f:
        t = Template(f.read())
        output = t.render(prefixes=src)
    return output

def generate_prefix_set(current_state:dict, template_path:str):

	src = []
	for k,v in current_state.items():
		if v == '1':
			src.append(k)
	with open(template_path, 'r', encoding='utf-8') as f:
		t = Template(f.read())
		output = t.render(prefixes=src)
	return output

def main():
	
	# TODO: Lock file

	logging.basicConfig(level=logging.INFO, filename='rpl_modify.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
	logging.info("rpl_modify starting...")

	LOCKFILE = '/tmp/rpl_modify.lock'

	if os.path.exists(LOCKFILE):
		logging.info("another instance of the script running, terminating")
		print("another instance of the script is running, terminating")
		sys.exit(1)
	else:
		with open(LOCKFILE, 'w') as f:
			pass

	argv = sys.argv[1:]
	
	try:
		opts, args = getopt.getopt(argv, 'p:a:u:', ['prefix=', 'action=', 'upstream='])
		if len(opts) == 0 or len(opts) > 3:
			print('Usage: rpl_modify.py -p <prefix> -a <action>')
			logging.error("Incorrect number of parameters given, terminating...")
			os.remove(LOCKFILE)
			sys.exit(1)
		else:
			for opt, arg in opts:
				if opt in ('-p', '--prefix'):
					prefix = arg
				if opt in ('-a', '--action'):
					action = arg
				if opt in ('-u', '--upstream'):
					upstream = arg
				else:
					upstream = None
	except getopt.GetoptError:
		print ('Usage: rpl_modify.py -p <prefix> -a <action> -u upstream')

    # Load inventory

	inventory = load_inventory()

	# Update system state

	current_state = update_state(prefix, action)
	
	# Generate prefix-set according to current system state
	
	prefix_set = generate_prefix_set(current_state, 'templates/template_prefix_set.html')

	if upstream:
		logging.info("Performing run for {}.".format(upstream))
		logging.info("Deploying to device")
		time.sleep(1)
		result = deploy(prefix_set, inventory[upstream]['device'])
		logging.info("Prefix-set has been deployed")
		logging.info("Post-run advertised prefix count check")
	else:
		for key, value in inventory.items():
			logging.info("Performing run for {}".format(key))
			logging.info("Deploying to device {}".format(value['device']))
			result = deploy(prefix_set, value['device'])

	os.remove(LOCKFILE)

if __name__ == "__main__":
    main()

