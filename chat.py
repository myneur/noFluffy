import openai

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

class Chat:
	def __init__(self):
		self.rec = Recorder()
		self.say = Synthesizer()
		self.ai = AI()
		self.minChars = 5
		self.guidance = """
– ENTER: start and stop listening
– n: new conversation
- t: new translation
– exit by Esc+Enter
"""
		

	def go(self): 
		print(self.guidance)

		while True:
			prompt = input()

			if self.rec.recording and len(prompt) == 0:
				file = self.rec.stop()
				print("…")
				
				text = self.ai.voice2text(file)
				os.system("clear")
				print(text); print()

				"""action = self.ai.classify(text)
				if action.lower() != "none"
					print("Action: "+ action)
					self.say.say("Action: "+ action)"""

				#if len(text.strip().split(" "))>1: ;#use it as commannd

				self.ask(text)


			elif prompt.lower() in['\x1b', "exit", "esc"]: # ESC
					break
			elif 'n' == prompt:
				self.ai.start()
				print("New conversation started")
			elif 't' == prompt:
				self.ai.start("translator")
				print("New translator started")
			else:
				if(len(prompt) >= self.minChars):
					self.ask(prompt)
				else:
					print("Speak!\r\nENTER to get reply!")
					self.say.stop()
					self.rec.rec()

	def ask(self, question):
		if len(question) < self.minChars:
			return question + " is not a question"
		response = self.ai.chat(question)
		print(self.enahance4screen(response))
		self.say.say(response)
		print(self.guidance)
		return response
	
	def enahance4screen(self, text):
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
		conf = yaml.safe_load(open('config.yaml', 'r'))
		self.languages = " or ".join(conf['languages'])
		AI.modes = conf['modes']

		self.start()
		with open('../private.key', 'r') as key:
			openai.api_key =  key.read().strip()


	def start(self, mode = 'assistant'):
		self.mode = mode
		if mode == 'classificator':
			param = AI.modes[mode]['modes']
		else:
			param = self.languages
		self.messages = [{"role": "system", "content": AI.modes[mode]['messages'][0]['system'].format(param)}]

	def voice2text(self, filename):
		audio_file= open(filename, "rb")
		transcript = openai.Audio.transcribe("whisper-1", audio_file)
		return transcript.text

	def chat(self, question):
		self.messages.append({"role": "user", "content": question})
		response = openai.ChatCompletion.create(
			model = "gpt-3.5-turbo",
			messages = self.messages,
			temperature = 0
		)
		reply = response["choices"][0]["message"]["content"]
		self.messages.append({"role": "assistant", "content": reply})
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

	def inlineFields(dictionaries):
		return '\n'.join(
	        '\n'.join(f"{key}:\n{dictionary[key]}\n" for key in dictionary.keys())
	        for dictionary in dictionaries
	    )
		#return '\n'.join(f"{key}:\n{dictionary[key]}\n" for key in dictionary.keys())

	def limit2keys(dictionaries, keys):
		return [{key: dictionary[key] for key in keys if key in dictionary} for dictionary in dictionaries]

	def getPrice(text):
		words = len(re.sub(r'\s+', ' ', text).split(" "))
		return "${: .1f} for {:,} words".format(words*tokenPrice, words)	

	def voice2excel(self, filename, fp16=False, n=5, op_name='transcribe'):
		audio_file= open(filename, "rb")
		transcript = openai.Audio.transcribe("whisper-1", audio_file)


		splitter = Splitter(transcript, n)
		splitter.save_as_excel(f'{op_name}.xlsx')

		return splitter.split_into_sentences_with_prompts()

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
		self.process = subprocess.Popen(["say", "-v", text_voice, text])
		return self.process

	def stop(self):
		if self.process: 
			self.process.kill()
			self.process = None

	def escape4shell(self, text):
		text = text.replace("`", "'")
		text = text.replace('"', "").replace("'", "")
		text = text.replace('$', "\\$")
		if text[0]=="-": # say considers starting - as a parameter
			text = "\\"+text
		return text
		

	def simply2read(self, text): 
		text = text.replace("\r", "")
		# remove code 
		text = re.compile(r"(```.*?```)", re.DOTALL).sub("Example code.\n", text)
		# remove tables in 2 steps before the first leaves EOLs for some reason
		text = re.compile(r"^\|.*?\|$", re.DOTALL|re.MULTILINE).sub("```", text)
		text = re.compile(r"```[`\n]*", re.DOTALL).sub("Example table.\n", text)
		return text


