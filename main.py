from dotenv import load_dotenv
import requests
import os
from functools import reduce 
from operator import mul
import json
import time
import os.path
import shutil
from datetime import datetime

def webdriver_test():
	from selenium import webdriver
	from selenium.webdriver.common.by import By
	from selenium.webdriver.common.keys import Keys
	from selenium.webdriver.chrome.options import Options
	from selenium.webdriver.support.ui import WebDriverWait
	from selenium.webdriver.support import expected_conditions as EC
	from selenium.common.exceptions import TimeoutException

	options = webdriver.ChromeOptions()
	if not os.getenv("DEBUG_MODE"):
		options.add_argument("--headless")
		options.add_argument('--disable-gpu')
	web_driver = None
	try:
		web_driver = webdriver.Chrome(executable_path=os.getenv('CHROME_DRIVER'), options=options)
	except Exception as e:
		print("couldn't start web driver", e)
	
	url = "https://sport.toto.nl/sport/resultaten"
	web_driver.get(url)

	try:
		w = WebDriverWait(web_driver, 8)
		w.until(EC.presence_of_element_located((By.CLASS_NAME,"sports-results")))
	except TimeoutException as e:
		print("Timeout happened no page load")

	results_filter = web_driver.find_element_by_class_name("result-filters")

	filter_groups = results_filter.find_elements_by_class_name("result-filters__group")

	for filter_group in filter_groups:
		label = filter_group.find_element_by_class_name("result-filters__label")
		label_text = label.get_attribute('innerHTML')
		print("input label: " + label_text)


def reshape(lst, shape):
	if len(shape) == 1:
		return lst
	n = reduce(mul, shape[1:])
	return [reshape(lst[i*n:(i+1)*n], shape[1:]) for i in range(len(lst)//n)]

def get_scaped_toto_ids():
	data = None
	try:
		with open(os.getenv("TOTO_RESULTS_FILE"), mode='r') as f:
			data = json.load(f)
			f.close()
		return list(map(lambda x: x['id'], data))
	except (json.decoder.JSONDecodeError, FileNotFoundError) as e:
		print("Didn't find any already scraped IDs")
		return []

def backup_scraped_toto():
	if not os.path.exists(os.getenv("TOTO_RESULTS_FILE")):
		return False
	
	if not os.path.exists('backups'):
		os.makedirs('backups')
	
	now = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
	output_path = 'backups/toto_' + str(now) +'.json'
	shutil.copyfile(os.getenv("TOTO_RESULTS_FILE"), output_path)
	return True

def write_entry_to_file(entry, output_file):
	# TODO: checking if file exists and is valid doesn't have to be done everytime..
	if not os.path.isfile(output_file):
		with open(output_file, mode='w') as f:
			f.write(json.dumps([entry], indent=2))
			return
	
	with open(output_file, mode='r+') as f:
		content = f.read()
		if (os.stat(output_file).st_size == 0):
			f.write(json.dumps([entry], indent=2))
			return

		# nasty insertion so can append and don't have to read entire file to ram evertime
		size = os.path.getsize(output_file)
		f.seek(size-2)
		json_stuff = "  " + json.dumps(entry, indent=2).replace("\n", "\n  ")
		f.write(",\n" + json_stuff + "\n]")

def toto_scrape(output_file, ids = list(range(0, 75445))):
	#ids =  list(range(0, 55445))
	already_scraped = get_scaped_toto_ids()
	ids = list(filter(lambda x: x not in already_scraped, ids))
	
	#batch IDs
	id_chunk_size = 100
	
	shape = [2, id_chunk_size]
	id_chunks = reshape(ids, shape)
	
	left_over_n = len(ids) % id_chunk_size
	if left_over_n > 0:
		left_overs = ids[len(id_chunks) * id_chunk_size : ]
		id_chunks.append(left_overs)

	#use IDs batches to grab data
	for chunk in id_chunks:
		id_chunks_str =','.join(map(str,chunk))
		url = "https://content.toto.nl/content-service/api/v1/q/resulted-events?eventIds="+ id_chunks_str +"&includeChildMarkets=true&includeRace=true&includeRunners=true"
		
		response = requests.get(url)

		if not response.status_code == 200:
			print("request failed: " + str(response.status_code) + "\n" + str(response.content))
			exit()
	
		results = response.json()['data']['eventResults']

		for result in results:
			name = result["name"]
			id = int(result["id"])
			cat = result['category']['name']
			start_time = result['startTime']
			print(str(id), cat, start_time, name)

			entry = {'id': id, 'result': result}
			write_entry_to_file(entry, output_file)


if __name__ == "__main__":
	load_dotenv()

	#write_entry_to_file({'id': 0, 'result': {}}, os.getenv("TOTO_RESULTS_FILE"))

	backup_scraped_toto()
	toto_scrape(os.getenv("TOTO_RESULTS_FILE"))