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
import asyncio
from pyppeteer import launch
import pyppeteer_stealth

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
import chardet
from unidecode import unidecode

from geopy.distance import geodesic as distance


demoString = """- You have a reply from Mark regarding designs, asking for ideas on how to present the product,
- important mails from Alex about upcoming product release plan and Serena about Strategy and growth.

- Then there 2 other unread and 34 read mails.

Do you want me to summarize them?
		"""

def ex(e):
	return f"{type(e).__name__}: {e}"

class Memory:
	def __init__(self, name='memory'):
		self.name = name
		if not hasattr(Memory, name):
			self.load()
		self.data = getattr(Memory, name)

	def load(self):
		try:
			with open(f'data/{self.name}.yaml', 'r') as file:
				setattr(Memory, self.name, yaml.safe_load(file))
		except:
			setattr(Memory, self.name, {})

	def save(self):
		with open(f'data/{self.name}.yaml', "w") as file:
			yaml.dump(getattr(Memory, self.name), file)


class Services:
	def __init__(self):
		self.APIkey = os.environ.get('GOOGLE_API_KEY')
		if not self.APIkey:
			self.APIkey = open('../google.key', "r").read()

		self.gmailKey = os.environ.get('GMAIL_API_KEY')
		if not self.gmailKey:
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

	def split_query_literal_filters(self, filters, mail_set='ALL', candidates=('subject', 'text', 'body')):
		if not filters:
			return mail_set
		query = ""
		fulltext_literal = {}
		candidates = set(candidates).intersection(set(filters.keys())) if candidates else set(filters.keys())			

		for k in candidates:
			it = filters[k]
			if not fulltext_literal and unidecode(it) != it:
				fulltext_literal = {'key': k, 'value': it}
				filters.pop(k)
				candidates.remove(k)
				break
			
		if candidates:
			if not fulltext_literal:
				first = list(candidates)[0]
				fulltext_literal = {'key': first, 'value': filters[first]}
				filters.pop(first)
				candidates.remove(first)
			for k in candidates:
				query += f'({k.upper()} "{filters[k]}") ' # TODO allow OR as well
				filters.pop(k)

		return query, fulltext_literal, filters

	def get_mails(self, query=None, literal=None, limit=100, headers=None):
		mail = imaplib.IMAP4_SSL('imap.gmail.com')
		mail.login(self.loginMail, self.gmailKey)
		mail.select("INBOX")
		if not (query or literal):
			query = 'ALL'
		try:
			if literal:
				mail.literal = literal['value'].encode('UTF-8')
				query += " "+literal['key']

			status, messages = mail.uid('search', 'UTF-8', query) # this bastard allow only one literal to pass

		except Exception as e:
			print(f"Error getting mails: {type(e).__name__}: {e}")
			print(query, literal, headers)
			return None

		try:
			print(len(messages[0].split()), "mails")
			messages = messages[0].split()
			if limit:
				messages = messages[:limit]

			mode = "(BODY.PEEK[HEADER.FIELDS ("+ ' '.join(headers)+")])" if headers else "(RFC822)"

			mails = []
			for message in messages:
				status, data = mail.uid("fetch", message, mode)
				if headers: 
					fields = data[0][1]
					encoding = chardet.detect(fields)
					fields = re.split("[\n\r]+", fields.decode(encoding['encoding']))
					data = {}
					for field in fields:
						f = field.split(':')
						if len(f)>1:
							data[f[0].lower()] = f[1]
				else:
					message = email.message_from_bytes(data[0][1])
					parts = message.walk() if message.is_multipart() else [message]
					for part in parts:
						if part.get_content_type() in ("text/plain", "text/html"):
							try:
								payload = part.get_payload(decode=True)
								encoding = chardet.detect(payload)
								data = payload.decode(encoding['encoding'], 'replace')
							except Exception as e:
								print(f"Error decoding mail: {type(e).__name__}: {e}")
							try: 
								# TODO make it robuts to languages nad different clients: \n<p>On Thu, Apr 13, 2023 at 12:49\u202fPM Petr Meissner aka myneur <a href="...">...</a>\nwrote:</p>\n<blockquote>\n<p>...
								data = self.remove_re(data)
							except: 
								print('no content')
				if data:
					mails.append(data)
		except Exception as e:
			print(f"{type(e).__name__}: {e} \n {str(query)}")
		finally:
			mail.close()
			mail.logout()
		
		return mails

	def read_mail_semantic(self, filters=None, limit=100):
		query, literal, filters = self.split_query_literal_filters(filters)
		print(query, literal, filters)
		candidates = self.get_mails(query, literal, limit=limit, headers=filters.keys())

		if filters:
			from ai import AI
			ai = AI()
			return ai.find_similar(candidates, filters)
		else:
			return candidates


	def remove_re(self, message):
		return re.split(r"\w+ \w+, \w+ \d+, \d+ \w+ \d+:\d+", message)[0]

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

						if field == 'SUBJECT': 
							field = f'(OR (SUBJECT "{keyword}") (BODY "{keyword}"))'
						else:
							field = f'{field} "{keyword}"'

						query.append(field)
			if len(query) == 0:
				query.append('ALL') #('UNSEEN', 'INBOX', 'ALL')
		try:
			#mail.literal = filters['subject'].encode('UTF-8')
			status, messages = mail.uid('search', None, 'CHARSET UTF-8', *query) # this bastard allow only one literal to pass

		except Exception as e:
			return {'content': f"{type(e).__name__}: {e} \n {str(query)}"}

		try:
			print(len(messages[0].split()), "mails")
			last_message = messages[0].split()[-1]

			#status, data = mail.fetch(last_message, '(RFC822)')
			status, data = mail.uid("fetch", last_message, "(RFC822)")
			#status, data = mail.uid("fetch", last_message, "(BODY[HEADER.FIELDS (FROM TO SUBJECT)])")

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

	def places(self, location, radius=1500, venueType=None):
		endpoint_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
		locStr = str(location[0])+'%2C'+str(location[1])

		# TODO opennow, keyword, rankby prominence|distance 
		
		request_url = f"{endpoint_url}?location={locStr}&radius={radius}&key={self.APIkey}"
		if venueType:
			request_url += '&type='+venueType
		response = requests.get(request_url)
		results = response.json()["results"]

		for i, result in enumerate(results):
			adr = result["vicinity"].split(',')
			street_index = 1 if adr[0][0].isdigit()else 0
			address = adr[street_index].strip()
			if street_index:
				address += ', ' + adr[0]
			results[i]['address'] = address
			
			if 'rating' not in result:
				results[i]['rating'] = 0
			
			venueLoc = result["geometry"]["location"]
			results[i]['distance']  = distance((venueLoc['lat'], venueLoc['lng']), location)
			# ['types'], ['place_id'], ['photos'][0]['photo_reference'], {location['lat']}, {location['lng']}

		sorted_results = sorted((results), key=lambda x: x['rating'], reverse=True)

		for result in sorted_results:
			print(f"{str(result['rating'])}* {result['name']}: {result['address']} @{result['distance'].km:.1f} km")


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

	def youtube(self, url, method=0):
		if method == 0:
			from pytube import YouTube
			yt = YouTube(url)
			audio_stream = yt.streams.filter(only_audio=True).first()
			audio_stream.download(filename_prefix="audio_")
			return audio_stream
		elif method == 1:
			import youtube_dl
			options = {
				'format': 'bestaudio/best',  # Download best available quality
				'postprocessors': [{
					'key': 'FFmpegExtractAudio',
					'preferredcodec': 'mp3',  # Save as mp3 (or 'wav', 'm4a' etc.)
					'preferredquality': '192',  # 192kbps
				}],
				'outtmpl': 'audio.mp3',  # Save the file as 'audio.mp3'
			}
			with youtube_dl.YoutubeDL(options) as ydl:
				return ydl.download([url])
		else: 
			import yt_dlp
			opts = {
				'format': 'bestaudio/best',
				'outtmpl': 'audio.%(ext)s',
				'postprocessors': [{
					'key': 'FFmpegExtractAudio',
					'preferredcodec': 'mp3',
				}],
			}
			with yt_dlp.YoutubeDL(opts) as ydl:
				return ydl.download([url])

	def url(self, url, tag="article"):
		response = requests.get(url)
		html_content = response.content

		soup = BeautifulSoup(html_content, 'html.parser')

		article = soup.find(tag)

		article_text = article.get_text()
		return article_text



	async def _web(self, url):
		browser = await launch()
		page = await browser.newPage()
		await pyppeteer_stealth.stealth(page)
		await page.goto(url)
		content = await page.content()
		return browser, page, content

	
		
		"""soup = BeautifulSoup(content, 'html.parser')
		h1_tags = soup.find_all('h1')
		for h1 in h1_tags:
			print(h1.text)"""

		"""
		elements = '//article[@data-testid="tweet"]//div[@data-testid="tweet"]//span'
		await page.waitForXPath(elements, timeout=10000)
		tweets = await page.xpath(elements)

		for tweet in tweets:
			text = await page.evaluate('(element) => element.textContent', tweet)
			print(text)"""

	def web_xpath(self, url, xpath=None):
		async def web(url, xpath=None):
			browser, page, content = await self._web(url)

			if xpath:
				elements = await page.xpath(f'//{xpath}')
				for elm in elements:
					text = await page.evaluate(f'(e) => e.textContent', elm)
					print(text)
			else:
				print(content)
			await browser.close()
		asyncio.run(web(url, xpath)) #f"//{parent_tag}[contains(@class,'{parent_class}')]//*[@id='{element_id}'and contains(@class,'{element_class}')]"
	

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

	def remove_long_literals(self, text):
		longish_literal = r"\b\S{26,}\b"
		return re.sub(longish_literal, lambda match: match.group()[:10]+"…", text)

	def remove_gibberish(self, text):
		gibberish = r'(\S*[=?]+\S*){26,}'
		return re.sub(gibberish, "", text)

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