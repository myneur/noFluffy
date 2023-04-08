import os
import subprocess 
import re
import pandas as pd
import json
import yaml

import requests
from bs4 import BeautifulSoup
#import newspaper

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart



class Google:
	def __init__(self):
		self.APIkey = open('../google.key', "r").read()
		self.gmailKey = open('../gmail.key', "r").read()


	def mailLast(self, data):
		me = 'Voicelet assistant<'+data['mail']+'>'
		subject = data['subject'] if 'subject' in data else "Note to myself"
		return self.mail(me, me, subject, data['message'])

	def mail(self, from_address, to_address, subject, body):
		loginMail = "myneur@gmail.com"

		smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
		smtp_server.starttls()
		smtp_server.login(loginMail, self.gmailKey)

		#message = f'Subject: {subject}\n\n{body}'
		msg = MIMEMultipart()
		msg['From'] = from_address
		msg['To'] = 'to_address'
		msg['Subject'] = subject
		msg.attach(MIMEText(body, 'plain'))


		smtp_server.sendmail(from_address, to_address, msg.as_string())

		smtp_server.quit()

		return True

	def populateTestMailbox(self):
		#mails = yaml.safe_load(open('logs/in.yaml', 'r'))
		to = "Petr Meissner <petr@sl8.ch>"
		mails = [{'Contact': "Mark", 'Subject':"Design Approval Request"}]
		if( input() == 'yes'):
			for mail in mails:
				from_address = mail['Contact'] + " <myneur@gmail.com>"
				print("{}: {}".format(mail['Contact'], mail['Subject']))
				self.mail(from_address, to, mail['Subject'], mail['Subject'])

	def summarizeMailbox(self):
		return """
- You have a reply from Mark regarding designs, asking for ideas on how to present the product,
- important mails from Alex about upcoming product release plan and Serena about Strategy and growth.

- Then there 2 other unread and 34 read mails.

Do you want me to summarize them?
		"""

	def scheduleMeeting(self, request):
		try:
			word_pattern = r'with\s+([\w\s]+?)in|at|for|to'
			match = re.search(word_pattern, request)
			recipients = match.group(1).strip()
			text = f"""Meeting with {recipients} scheduled at 5 pm """
		except:
			text = """Meeting scheduled at 5 pm """			

		return text


	def test(self, type="restaurant"):
		endpoint_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
		location = '50.1%2C14.4'

		radius = 500
		opennau = True
		type ='restaurant'

		request_url = f"{endpoint_url}?location={location}&radius=50000&key={self.APIkey}"
		print(request_url)
		params={
			'keyword':'restaurants',
			'type':'restaurant',
			'location':location, 
			'radius':radius,
			'key':self.APIkey}
		print(params)
		#response = requests.get(request_url)
		response = requests.get(endpoint_url, params=params)
		print(response.status_code)
		print(response)


		results = response.json()["results"]
		print(results)
		for result in results:
			name = result["name"]
			location = result["geometry"]["location"]
			print(f"{name}: ({location['lat']}, {location['lng']})")

	def restaurants(self, type="restaurant"):
		endpoint_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
		location = '50.1%2C14.4'

		radius = 500
		opennau = True
		type ='restaurant'

		request_url = f"{endpoint_url}?location={location}&radius=50000&key={self.APIkey}"
		print(request_url)
		params={
			'keyword':'restaurants',
			'type':'restaurant',
			'location':location, 
			'radius':radius,
			'key':self.APIkey}
		print(params)
		#response = requests.get(request_url)
		response = requests.get(endpoint_url, params=params)
		print(response.status_code)
		print(response)


		results = response.json()["results"]
		print(results)
		for result in results:
			name = result["name"]
			location = result["geometry"]["location"]
			print(f"{name}: ({location['lat']}, {location['lng']})")





class Splitter:
	def __init__(self, text, n):
		self.text = text
		self.n = n

	def split_into_sentences_with_prompts(self):
		print(self.text)
		print(type(self.text))
		if self.text == "":
			raise ValueError("Input text cannot be empty.")
		if self.n <= 0:
			raise ValueError("n must be a positive integer.")
		sentences = re.split("(?<=[.!?]) +", self.text['text'])
		if len(sentences) < self.n:
			raise ValueError("Input text must have at least n sentences.")
		prompts = sentences[::self.n]
		completions = []
		for i in range(len(prompts) - 1):
			completion = " ".join(sentences[self.n * i + 1:self.n * (i + 1)])
			completions.append(completion)
		completions.append(" ".join(sentences[self.n * (len(prompts) - 1) + 1:]))
		data = {'prompt': prompts, 'completion': completions}
		df = pd.DataFrame(data)
		return df

	def save_as_excel(self, filename):
		df = self.split_into_sentences_with_prompts()
		df.to_excel(filename, index=False)

	def save_as_csv(self, filename):
		df = self.split_into_sentences_with_prompts()
		df.to_csv(filename, index=False)

	def save_as_json(self, filename):
		df = self.split_into_sentences_with_prompts()
		data = []
		for i in range(len(df)):
			row = {'prompt': df.iloc[i]['prompt'], 'completion': df.iloc[i]['completion']}
			data.append(row)
		with open(filename, 'w') as f:
			json.dump(data, f)




class Scraper:
	def YTAudio(self, url):
		yt = YouTube(url)
		audio_stream = yt.streams.filter(only_audio=True).first()
		audio_stream.download(filename_prefix="audio_")
		return audio_stream

	def webContent(self, url, tag="article"):
		response = requests.get(url)
		html_content = response.content

		soup = BeautifulSoup(html_content, 'html.parser')

		article = soup.find(tag)

		article_text = article.get_text()
		return article_text

	"""def articleContent(self, url):
		article = newspaper.Article(url)
		article.download()

		article.parse()
		return article.text"""


class Logger:
	logs = None

	def __init__(self):
		if not Logger.logs:
			try:
				if not Logger.logs:
					Logger.logs = open('logs/log.yaml', 'a+')
			except FileNotFoundError as e:
				print(e)

	def log(self, text):
		try:
			Logger.logs.write(text+'\n') # TODO concurrent use
		except Exception as e:
			print('Logging failed: '+e)

	def logDataStructure(self, dataStructure, filename="output"):
		dataStructure = dataStructure.strip()
		try:
			if dataStructure[0] == "{":
				print('JSON')
				try:
					json = json.loads(dataStructure)
					print(json)
				except:
					print("not valid")
					print(dataStructure)
			elif re.match(r"\w+:", dataStructure):
				try:
					print('YAML')
					print(dataStructure)
					json = yaml.load(response, Loader=yaml.FullLoader)
					print(json)
					#re.compile(r"(```.*?```)", re.DOTALL).sub("Example code.\n", text)
				except:
					print("not valid")
					print(dataStructure)
			else:
				print("TXT")
				for line in dataStructure.splitlines():
					print("- "+ line)

		except Exception as e:
			print(e)

class Convertor:
	def __init__(self):
		self.listKey = '_list'

	# convert a GPT output that is supposed to be YAML into a JSON while being tolerant to invalid lines and multilines
	def yaml2json(self, text, defaultTag=None): 
		json = {}
		lastTag = defaultTag	# used when first lines are without any tag
		listKey = self.listKey

		# what to tolerate as id
		# 1_2_words = r"^\w+\s?\w*:"
		#1_2_words_w_quotes = r"^[\s\"\']*\w+[\s\"\']*:"
		compound_words_n_quotes = r"^[\s\"\']*[\w\-_]+[\s\"\']*:"
		blanks_n_quotes = re.compile(r"['\"\s]", re.DOTALL)
		list_item = r"\s*(-|\d+[\.)])\s*"

		for line in text.splitlines():
			line = line.strip()

			try:
				# identifier
				if re.match(compound_words_n_quotes, line):
					yam = line.split(":", 1)
					ident = self.stripQuotes(yam[0]).lower()
					ident = blanks_n_quotes.sub('', ident)
					json[ident] = self.stripQuotes(yam[1])
					lastTag = ident

				# list
				elif re.match(list_item, line):
					if listKey not in json:
						json[listKey] = []
					json[listKey].append(self.stripQuotes(re.split(list_item, line, 1)[2]))
					lastTag = listKey

				# multilines to be passed to preivous ident
				elif lastTag: 
					if lastTag not in json:
						json[lastTag] = [line] if lastTag == listKey else line
					else:
						if lastTag == listKey:
							json[lastTag][-1] += "\n"+line
						else:	
							json[lastTag] += "\n"+line
			except Exception as e:
				print("Error" + e)
		return json if json else None

	def stripQuotes(self, text):
		text = text.strip()
		if text.startswith(("'", '"')) and text[0] == text[-1]:
			text = text[1:-1]
		return text

	def saveAsCases(self, cases, expectedValue, model):
		ok = "\n-   ok: "
		q = "\n    q: |\n        "

		try: 
			if self.listKey in cases:
				cases = cases[self.listKey]
		except:
			print("Error: That's not a list!")

		filename = f"testdata/{model}.yaml"
		try:
			with open(filename, 'a+') as file:
				for case in cases:
					file.write(ok + expectedValue)
					file.write(q + case)
			print(f"{len(cases)} saved to {filename}")

		except Exception as e:
			print(e)

	def translation(self, text, defaultTag=None):
		json = self.yaml2json(text, defaultTag)
		output = json['translation']+"\n"
		output += f">>> from: {json['from']}, to: {json['to']} <<<"
		return output


"""	def toJSON(self, text):
		try:
			yam = self.jsonize(text)
			son = self.yamlize(text)
			lines = ["- "+line for line in dataStructure.splitlines() if line.strip()]

			return 
		except Exception as e:
			print(e)
			return None

	def yamlize(self, text):
		yaml_lines = []
		for line in text.splitlines():
			try:
				yaml.safe_load(line)
				yaml_lines.append(line)
			except yaml.YAMLError:
				pass
		return yaml.safe_load('\n'.join(yaml_lines)) if yaml_lines else None

	def jsonize(text):
		json_lines = []
		for line in text.splitlines():
			try:
				json.loads(line)
				json_lines.append(line)
			except json.JSONDecodeError:
				pass
		return json.loads('{%s}' % ', '.join(json_lines)) if json_lines else None"""
		


class Stats:
	stats = None

	def __init__(self):
		if not Stats.stats:
			Stats.stats = {}
		self.last = {}

	def add(self, dictionary, what='general'):
		if what not in Stats.stats.keys():
			Stats.stats[what] = {'items':0}

		stat = Stats.stats[what]
		for key in dictionary.keys():
			if key not in stat.keys():
				stat[key] = float(dictionary[key])
			else:
				stat[key] += float(dictionary[key])

		self.last[what] = dictionary

	def print(self):
		output = "- stats:\n"
		for mode in list(Stats.stats.keys()):
			stat = Stats.stats[mode]
			items = int(stat['items'])
			if items:
				output += f'    {mode}:\n'
				for key in list(stat.keys()):
					if key == 'items':
						output += f'      - items:{items}\n'
					else:
						output += "      - ⌀{}: {}\n".format(key, round(stat[key]/items, 1))
		print(output)
		return output