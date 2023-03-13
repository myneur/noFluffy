import os
import subprocess 
import re
import pandas as pd
import json

import requests
from bs4 import BeautifulSoup
import newspaper

class Google:
	def __init__(self):
		self.key = open('../google.key', "r").read().strip()
		
		

	def test(self, type="restaurant"):
		endpoint_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
		location = '50.1%2C14.4'

		radius = 500
		opennau = True
		type ='restaurant'

		request_url = f"{endpoint_url}?location={location}&radius=50000&key={self.key}"
		print(request_url)
		params={
			'keyword':'restaurants',
			'type':'restaurant',
			'location':location, 
			'radius':radius,
			'key':self.key}
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

		request_url = f"{endpoint_url}?location={location}&radius=50000&key={self.key}"
		print(request_url)
		params={
			'keyword':'restaurants',
			'type':'restaurant',
			'location':location, 
			'radius':radius,
			'key':self.key}
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

	def articleContent(self, url):
		article = newspaper.Article(url)
		article.download()

		article.parse()
		return article.text

