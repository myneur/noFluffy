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
		mails = yaml.safe_load(open('logs/in.yaml', 'r'))
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