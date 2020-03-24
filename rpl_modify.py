import json
import getopt
import sys
import logging
from jinja2 import Template
from ncclient import manager

# const

TEMPLATE_DIR = 'templates'

template_mapping = {
    'gtt': {'template_path': "{}/template_gtt.html".format(TEMPLATE_DIR),
            'device': '10.98.23.2'},
    'decix': {'template_path': "{}/template_decix.html".format(TEMPLATE_DIR),
              'device': '10.98.23.2'},
    'century_prague': {'template_path': "{}/template_century_prague.html".format(TEMPLATE_DIR),
                        'device': '10.98.23.2'},
    'century_warsaw': {'template_path': "{}/template_century_warsaw.html".format(TEMPLATE_DIR),
                       'device': '10.98.23.2'},
    'cogent': {'template_path': "{}/template_cogent.html".format(TEMPLATE_DIR),
               'device': '10.98.23.2'},
	'epix': {'template_path': "{}/template_epix.html".format(TEMPLATE_DIR),
			 'device': '10.98.23.2'},
	'plix': {'template_path': "{}/template_plix.html".format(TEMPLATE_DIR),
			 'device': '10.98.23.2'}
}

def read_state():

    """
    Odczytuje stan z pliku.

    """
    with open("state.json", encoding="utf-8") as f:
        input = json.load(f)
    return input

def write_state(state:json):

    """
    Zapisuje stan do pliku.

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
    Laduje konfiguracje na wskazany router za pomoca NETCONF.
    :param rpl_config:
    :return:
    """
    with manager.connect(host=device, port=830, username="cisco", password="cisco",
                         device_params={'name': 'iosxr'}, hostkey_verify=False, allow_agent=False,
                         look_for_keys=False) as nc_conn:
        nc_reply = nc_conn.edit_config(target="candidate", config=rpl_config)
        nc_reply = nc_conn.commit()
        #  nc_config = nc_conn.get(('subtree', ncc_filter))
        print(nc_reply)

def generate_rpl(upstream:str, current_state:dict, template_path:str):

    """
    Generuje nowa RPL na podstawie template'u.
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

def main():
	
	# TODO: Lock file
	# TODO: Logging - dlaczego pozostale moduly podpinaja sie pod logi?

	logging.basicConfig(level=logging.DEBUG, filename='rpl_modify.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
	logging.info("rpl_modify starting...")
	argv = sys.argv[1:]
	
	try:
		opts, args = getopt.getopt(argv, 'p:a:u:', ['prefix=', 'action=', 'upstream='])
		if len(opts) == 0 or len(opts) > 3:
			print('Usage: rpl_modify.py -p <prefix> -a <action>')
		else:
			for opt, arg in opts:
				if opt in ('-p', '--prefix'):
					prefix = arg
				if opt in ('-a', '--action'):
					action = arg
				if opt in ('-u', '--upstream'):
					upstream = arg
	except getopt.GetoptError:
		print ('Usage: rpl_modify.py -p <prefix> -a <action> -u upstream')

    # Odczytujemy z pliku aktualny stan systemu i aktualizujemy go zgodnie z przekazanymi parametrami
	
	current_state = update_state(prefix, action)
	
	# Generujemy RPL dla aktualnego stanu systemu

	print(upstream)
	if upstream:
		output = generate_rpl(upstream, current_state, template_mapping[upstream]['template_path'])
		print(output)
		result = deploy(output, template_mapping[upstream]['device'])
	else:
		for key, value in template_mapping.items():
			print(key)
			output = generate_rpl(key, current_state, value['template_path'])
			print(output)
			result = deploy(output, value['device'])


if __name__ == "__main__":
    main()

