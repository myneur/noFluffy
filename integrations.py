import os
import subprocess 
import re
import pandas as pd
import json
import yaml

import requests
from bs4 import BeautifulSoup
#import newspaper
#import markdown
#from rich.markdown import Markdown
import html2text

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
import chardet
from unidecode import unidecode

from pytube import YouTube

demoString = """- You have a reply from Mark regarding designs, asking for ideas on how to present the product,
- important mails from Alex about upcoming product release plan and Serena about Strategy and growth.

- Then there 2 other unread and 34 read mails.

Do you want me to summarize them?
		"""

class Memory:
	def __init__(self):
		self.load()

	def load(self):
		with open('data/memory.yaml', 'r') as file:
			Memory.data = yaml.safe_load(file)

class Services:
	def __init__(self):
		self.APIkey = open('../google.key', "r").read()
		self.gmailKey = open('../gmail.key', "r").read()

		self.memory = Memory()

		self.loginMail = self.memory.data['me']['mail']


	def send_mail(self, from_address, to_address, subject, body):
		smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
		smtp_server.starttls()
		smtp_server.login(self.loginMail, self.gmailKey)

		#message = f'Subject: {subject}\n\n{body}'
		msg = MIMEMultipart()
		msg['From'] = from_address
		msg['To'] = 'to_address'
		msg['Subject'] = subject
		msg.attach(MIMEText(body, 'plain'))

		smtp_server.sendmail(from_address, to_address, msg.as_string())

		smtp_server.quit()

		return True

	def read_mail(self, filters=None):
		""" gets the last mail according to either IMAP criteria strong or dictionary """
		mail = imaplib.IMAP4_SSL('imap.gmail.com')
		mail.login(self.loginMail, self.gmailKey)
		mail.select("INBOX")

		if type(filters) == str:
			query = filters
		else:
			query = []
			if type(filters) is dict:
				for key in filters.keys():
					field = key.upper()
					keyword = filters[key]
					if field in ('FROM', 'TO', 'SUBJECT'): # TODO we only support these filters so far
						if keyword.lower() in ('none', ''):
							break

						keyword = unidecode(keyword)
						#keyword = imaplib.IMAP4.literal(keyword).decode('utf-8')
						#keyword = keyword.encode('utf-8')

						#f'(OR FROM "*{keyword}*" header FROM *{keyword}*)'
							
						if field == 'SUBJECT': 
							field = f'(OR (SUBJECT "{keyword}") (BODY "{keyword}"))'
						else:
							field = f'{field} "{keyword}"'

						#field = field.encode('utf-8')
						query.append(field)
			if len(query) == 0:
				query.append('ALL')
		try:

			#search_query = f'X-GM-RAW "from:*{keyword}* to:*{keyword}* subject:*{keyword}*"'
			#search_query = f'X-GM-RAW "subject:*Krkonosich*"'
			#mail.literal = filters['subject'].encode('UTF-8')
			#status, messages = mail.uid('search', None, 'CHARSET UTF-8 SUBJECT')
			#status, messages = mail.search(None, search_query)

			status, messages = mail.search('utf-8', *query)
			#status, messages = mail.search(None, 'X-GM-RAW', *query)

		except Exception as e:
			return {'content': f"{type(e).__name__}: {e} \n {str(query)}"}

		#filters.encode('utf-8')
		#unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')

		try:
			last_message = messages[0].split()[-1]

			status, data = mail.fetch(last_message, '(RFC822)')
			#status, data = mail.uid("fetch", last_message, "(RFC822)")


			message = email.message_from_bytes(data[0][1])
		except:
			mail.close()
			mail.logout()
			try:
				query = ' '.join(query.decode())
			except:
				pass
			return {'content': "no such mail matches: "+str(query)}

		content = ""
		
		#content = message.get_payload()

		parts = message.walk() if message.is_multipart() else [message]
		for part in parts:
			if part.get_content_type() in ("text/plain", "text/html"):
				try:
					payload = part.get_payload(decode=True)
					detected_encoding = chardet.detect(payload)
					text = payload.decode(detected_encoding['encoding'])
				except Exception as e:
					print(f"Error: {type(e).__name__}: {e}")
				try: 
					# TODO make it robuts to languages nad different clients: \n<p>On Thu, Apr 13, 2023 at 12:49\u202fPM Petr Meissner aka myneur <a href="...">...</a>\nwrote:</p>\n<blockquote>\n<p>...
					text = re.split(r"\w+ \w+, \w+ \d+, \d+ \w+ \d+:\d+", text)[0]
				except: 
					print('no content')
				content = text

		"""for i, c in enumerate(content):
			print(i)
			print(c)"""
		
		content = html2text.html2text(content)

		message['content'] = content

		mail.close()
		mail.logout()
		return message


	def summarize_mailbox(self):
		return demoString

	def schedule_meeting(self, request):
		try:
			word_pattern = r'with\s+([\w\s]+?)in|at|for|to'
			match = re.search(word_pattern, request)
			recipients = match.group(1).strip()
			text = f"""Meeting with {recipients} scheduled at 5 pm """
		except:
			text = """Meeting scheduled at 5 pm """			

		return text

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

	def youtube(self, url):
		yt = YouTube(url)
		audio_stream = yt.streams.filter(only_audio=True).first()
		audio_stream.download(filename_prefix="audio_")
		return audio_stream

	def web(self, url, tag="article"):
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

class Convertor:
	def __init__(self):
		self.listKey = '_list'

	# convert a GPT output that is supposed to be YAML into a JSON while being tolerant to invalid lines and multilines
	def yaml2json(self, text, defaultTag=None): 
		if text == None: 
			return None
		json = {}
		lastTag = defaultTag	# used when first lines are without any tag
		listKey = self.listKey

		# what to tolerate as id
		# 1_2_words = r"^\w+\s?\w*:"
		#1_2_words_w_quotes = r"^[\s\"\']*\w+[\s\"\']*:"
		compound_words_n_quotes = r"^[\s\"\'\-]*[\w\-_]+[\s\"\']*:"
		blanks_n_quotes = re.compile(r"['\"\s]", re.DOTALL)
		list_item = r"\s*(-|\d+[\.)])\s*"

		for line in text.splitlines():
			line = line.strip()

			try:
				# identifier
				if re.match(compound_words_n_quotes, line):
					yam = line.split(":", 1)
					ident = self.strip_quotes(yam[0]).lower()
					ident = blanks_n_quotes.sub('', ident)
					json[ident] = self.strip_quotes(yam[1])
					lastTag = ident

				# list
				elif re.match(list_item, line):
					if listKey not in json:
						json[listKey] = []
					json[listKey].append(self.strip_quotes(re.split(list_item, line, 1)[2]))
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

	def strip_quotes(self, text):
		text = text.strip()
		if text.startswith(("'", '"')) and text[0] == text[-1]:
			text = text[1:-1]
		return text

	def remove_empty(self, dictionary):
		new = {}
		for key in dictionary.keys():
			if dictionary[key].lower().replace('none', ''):
				new[key] = dictionary[key]
		return new


	def links_to_preview(self, text):
		link = r"(https?://)?([a-z0-9-]+\.)+([a-z]{2,})(/[^\s]*)?"
		return re.sub(link, r"\2\3…", text)

	def save_cases(self, cases, model, expectedValue):
		ok = "\n- Equals: "
		q = "\n  q: |\n    "

		try: 
			if self.listKey in cases:
				cases = cases[self.listKey]
		except:
			print("Error: That's not a list!")

		filename = f"testdata/{model.strip()}.yaml"
		try:
			with open(filename, 'a+') as file:
				for case in cases:
					file.write(ok + expectedValue.strip())
					file.write(q + case)
			print(f"{len(cases)} saved to {filename}")

		except Exception as e:
			print(e)

	def first_sentences(self, text):
		firstSentences = re.split(r'(?<=\w[.?^!]) +(?=\w)', text)
		firstSentences = ".".join(firstSentences[:2])
		if len(firstSentences)<200:
			firstSentences = text[:200]
		return firstSentences

	def split_to_MD_blocks(_, text):
		objectTypes = {
			'code': r'(?m)^\s*```(\w*)([\s\S]*?)```\s*$', 
			'list': r"^(?: *[\*\-+]|\d+\.)[^\n]*$", 
			'table': r"^[|].*[|]$([\n^[|].*[|]$]+)?"}

		
		#blocks = [{'type': 'none', 'text': text}]
		# TODO detect all markdown

		objects = re.split(objectTypes['code'], text)
		i = 0
		for i, item in enumerate(objects): 
			objects[i] = {'text': item} 
			if i%2:
				objects[i]['type'] = 'code'#+ match.group(1)
			else:
				objects[i]['type'] = 'text'
				#console.print(block, style=Style(bgcolor="gray"))

		#linelength = len(text.split('\n')[0])
		#text = re.sub(codeblocks, r'\n' + '–'*10 + r'\n```\1```\n' + '–'*10 + '\n', text)
		#text = Markdown(text)
		blocks = objects
		return blocks

	def WIPblocksOfMD(self, text):
		# match all markers by regexp
		markers = [
			[r"```", "```"],
			[r"\d+\.\s+", "\n\n"],
			[r"-\s+", "\n\n"], 
			[r"\|", "|\n\n"]]


		#markers = [r'(?m)^\s*```([\s\S]*?)```\s*$', r'^-\s+']
		
		"""for m in markers: 
			blocks = re.split(m)
		"""
		for m in markers: 
			m[0] = re.compile(m[0])
		blocks = []
		marker = False
		lines = 0

		for line in text.splitlines():
			if marker:
				if not re.search(marker[1], line):
					blocks[-1] += "\n"+line
				else:
					marker = False
					blocks[-1] += line
					blocks.append('')
			else:
				for k in markers: 
					if re.search(k[0], line):
						marker = k
						blocks.append(line)
						break
				if not marker:
					if not len(blocks):
						blocks.append('')
					blocks[-1] += "\n" + line
		return blocks

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