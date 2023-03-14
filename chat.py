import openai

import time

import sounddevice as sd
import soundfile as sf
from langdetect import detect

import os
import subprocess 
import re
import yaml

import requests

#import termios, tty, sys # keyboard

from rich import print
import markdown	

import integrations

class Chat:
	def __init__(self):
		self.rec = Recorder()
		self.say = Synthesizer()
		self.ai = AI()
		self.google = integrations.Google()

		self.classificator = True

		self.minChars = 5

	def go(self): 
		self.guide()

		while True:
			prompt = input()

			# ask by voice
			if self.rec.recording and len(prompt) == 0:
				file = self.rec.stop()
				
				text = self.ai.voice2text(file)
				os.system("clear")
				print(text); print()
				self.run(text)


			# Service controls
			elif prompt.lower() in['\x1b', 'exit', 'esc']: # ESC
				break
			elif 'c' == prompt:
				mode = self.ai.start()
				print(f'New {mode} started')
			elif '<' == prompt:
				self.ai.loadConfig()
			elif 'f' == prompt:
				self.classificator = not self.classificator
				print(f'Classifying: {self.classificator}')
			elif 'mail' == prompt:
				last = self.ai.lastReply()
				if last:
					print('Sent') if self.google.mailLast(last) else print('Failed')
				else: 
					print('No messages')
			elif prompt in AI.modes.keys():
				self.ai.start(prompt)
			

			# ask by text prompt
			else:
				if 'repeat' == prompt: #repeating question
					self.run()
				elif len(prompt) >= self.minChars:
					self.run(prompt)
				
				# start listening
				else:
					print('Speak!\r\nENTER to get reply!')
					self.say.stop()
					self.rec.rec()

	def run(self, question=None):
		
		if self.classificator:
			action = self.ask(question, mode='classificator')
			action = re.sub(r'[,.]', "", action.strip().lower())
			print(f'classified as {action}')

			if action == 'none':
				print('asking question')
				response = self.ask(question)

			elif action == 'communicate':
				print('Preparing mail')
				response = self.ai.chat(question, mode='messenger')
				print('Sending mail')
				self.google.mailLast({'message':response, 'mail':self.ai.me['mail']})
			else :
				response  =f'I recognize that you ask about {action}. Functions related to it will be implemented in the future. Please be patient.'

		else:
			response = self.ask(question)
			
		self.reply(response)

		return response

	def reply(self, response):
		print(self.enahance4screen(response))			
		self.say.say(response)
		self.guide()

	def ask(self, question=None, mode=None):
		print("…")
		
		if question and len(question) < self.minChars:
			return question + ' is not a question'
		return self.ai.chat(question, mode)


	def guide(self):
		options = list(AI.modes.keys())
		options.remove(self.ai.mode)
		options.remove('classificator')

		print("\nI'm '{}'{}. Switch to {}".format(self.ai.mode, ' with classification' if self.classificator else '', str(options)))
		print("""– 'Listen': ENTER to start and stop
– 'Exit': Esc+Enter
- 'Functions': f
– 'Clear communication': r

""")
	
	def enahance4screen(_, text):
		pattern = r'(?m)^\s*```([\s\S]*?)```\s*$'
		linelength = len(text.split('\n')[0])
		return re.sub(pattern, r'\n' + '–'*linelength + r'\n\1\n' + '–'*linelength + '\n', text)



	"""def start(self):
		print(self.guidance)
		old_settings = termios.tcgetattr(sys.stdin)
		rec = self.rec
		ai = self.ai
		say = self.say

		try:
			tty.setraw(sys.stdin)
			while True:
				ch = sys.stdin.read(1)

				if rec.recording:
					file = rec.stop()
					print("…", end="\r\n")
					text = ai.voice2text(file)
					print(text, end="\r\n")
					re = ai.chat(text)
					print(re, end="\r\n")
					say.say(re)
					print(self.guidance, end="\r\n")

				elif ch == "\r":
					print("Speak!", end="\r\n")
					rec.rec()
				if ch == 'n':
					ai.clear_messages()
					print("New conversation started", end="\r\n")
				if ch == "\x1b":
					break
		finally:
			termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)"""


class AI:
	modes = None

	def __init__(self):
		self.mode = "assistant"
		self.loadConfig()
		self.start()
		with open('../private.key', 'r') as key:
			openai.api_key =  key.read().strip()


	def start(self, mode=None):
		self.mode = mode if mode else list(AI.modes.keys())[0]

		# TODO convert messages at func
		if mode == 'classificator':
			param = AI.modes[mode]['modes']
		else:
			param = self.languages
		self.messages = [{"role": "system", "content": AI.modes[self.mode]['messages'][0]['system'].format(param)}]

		return self.mode

	def voice2text(self, filename):
		audio_file= open(filename, "rb")
		transcript = openai.Audio.transcribe("whisper-1", audio_file)
		return transcript.text

	def chat(self, question=None, mode=None):
		# standard question
		if not mode: 
			mode = self.mode
			messages = self.messages
		# one time ask like for classification
		else: 

			# TODO convert messages at func
			if mode == 'classificator':
				param = AI.modes[mode]['modes']
			else:
				param = self.languages
			messages = [{"role": "system", "content": AI.modes[mode]['messages'][0]['system'].format(param)}]

		if(question): 
			messages.append({"role": "user", "content": question})
		# if no question, ask the last one again
		elif messages: 
			messages.pop(-1)

		response = openai.ChatCompletion.create(
			model = "gpt-3.5-turbo",
			messages = messages,
			temperature = 0
		)

		print("…")

		reply = response["choices"][0]["message"]["content"]
		
		# store messages if in standard chain
		if not mode: 
			messages.append({"role": "assistant", "content": reply})
			self.messages = messages
		return reply

	def chatStream(self, question):
		self.messages.append({"role": "user", "content": question})
		response = openai.ChatCompletion.create(
			model = "gpt-3.5-turbo",
			messages = self.messages,
			temperature = 0,
			stream = True
		)
		#reply = response["choices"][0]["message"]["content"]

		for message in response:
			if "choices" in message:
				if 'content' in message["choices"][0]["delta"]:
					text = message["choices"][0]["delta"]["content"]
					print(text)
			elif "error" in message:
				print(message["error"]["message"])
			time.sleep(0.1) # not sure what time should be used not to hit rate limiting. 
		#self.messages.append({"role": "assistant", "content": reply})
		return reply

	def classify(self, text):
		response = openai.ChatCompletion.create(
			model = "gpt-3.5-turbo",
			messages = [{"role": "user", "content": self.classificator + text}],
			temperature = 0
		)
		classifiedAs = response["choices"][0]["message"]["content"]
		return classifiedAs

	def completion(self, prompt):
		response = openai.Completion.create(
			engine = "text-davinci-003",
			prompt = prompt,
			max_tokens = 1024,
			n = 1,
			stop = None,
			temperature = 0, # from deterministic to creative
			top_p = 1,
			stream = False
		)
		reply = response["choices"][0]["text"]
		return reply

	def getPrice(text):
		words = len(re.sub(r'\s+', ' ', text).split(" "))
		return "${: .1f} for {:,} words".format(words*tokenPrice, words)	

	def lastReply(self):
		if len(self.messages)<1 or self.messages[-1]['role'] != 'assistant':
			return None
		
		return {
			'mail': self.me['mail'],
			'message': self.messages[-1]['content']}

	def loadConfig(self):
		conf = yaml.safe_load(open('config.yaml', 'r'))
		self.languages = " or ".join(conf['languages'])
		self.me = conf['me']
		AI.modes = conf['modes']

class Recorder:
	def __init__(self):
		self.format = 'mp3'
		self.sample_rate = 44100
		self.file = os.path.expanduser("~/Downloads/")+"temp."+self.format
		self.stream = sd.InputStream(samplerate=self.sample_rate, channels=1, blocksize=1024, callback=self.callback)
		self.recording = False
		self.audio = []


	def rec(self):
		self.clear_recordings()
		if not self.recording:
			self.recording = True
			self.stream.start()

	def stop(self):
		if self.recording:
			self.recording = False
			self.stream.stop()
			audio_samples = [samplearray for array in self.audio for samplearray in array]
			sf.write(self.file, audio_samples, self.sample_rate, format=self.format)
			return self.file
	
	def clear_recordings(self):
		self.audio = []

	def play(self):
		sd.play(self.file, self.sample_rate)

	def callback(self, indata, frames, time, status):
		if status:
			print(status, file=sys.stderr)
		if self.recording:
			self.audio.append(indata.copy())

class Synthesizer:
	def __init__(self): 
		self.voices = {
			'cs': "Zuzana", 
			'en': "Serena"}
		self.process = None

	def say(self, text):		
		try:
			lang = detect(text[:100])
			text_voice = self.voices[lang]
		except Exception: 
			text_voice = self.voices['en']

		text = self.escape4shell(self.simply2read(text))

		#os.system(f'say -v "{text_voice}"  "{text}"')
		self.process = subprocess.Popen(["say", "-v", text_voice, text, "-r", "240"])
		return self.process

	def stop(self):
		if self.process: 
			self.process.kill()
			self.process = None

	def escape4shell(self, text):
		text = text.replace("`", "'")
		text = text.replace('"', "").replace("'", "")
		text = text.replace('$', "\\$") 
		text = text.replace('!', "\\!") 
		if text[0]=="-": # say considers starting - as a parameter
			text = "\\"+text
		return text
		

	def simply2read(self, text): 
		text = text.replace("\r", "")
		
		# remove code blocks
		text = re.compile(r"(```.*?```)", re.DOTALL).sub("Example code.\n", text)
		
		# keep just first lines of table
		#text = re.compile(r"^\|.*?\|$", re.DOTALL|re.MULTILINE).sub("Example table.\n", text) # matches lines despite MULTLINE

		l = 0
		processed = ""
		for line in text.splitlines():
			if re.match(r"^\|.*\|$", line.strip()):
				l += 1
			else:
				l = 0;

			if l <= 4:
				processed += line +'\n'
				
		return processed