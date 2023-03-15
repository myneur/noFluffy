import openai

import time

import sounddevice as sd
import soundfile as sf
from langdetect import detect

import os
import subprocess 
import re
import yaml

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
				print('…')
				text = self.ai.voice2text(file)
				os.system("clear")
				print(text); print()
				self.run(text)

			# Service controls
			elif prompt.lower() in['\x1b', 'exit', 'esc']: # ESC
				break
			elif prompt.isdigit():
				self.ai.clearMessages(int(prompt))
				print("Only last {} messages kept".format(prompt))
			elif '<' == prompt:
				self.ai.loadConfig()
			elif 'f' == prompt:
				self.classificator = not self.classificator
				print(f'Functions: {self.classificator}')
			elif 'm' == prompt:
				for message in self.ai.messages:
					print(message['content'])
			elif 'mail' == prompt:
				last = self.ai.getLastReply()
				if last:
					print('Sent') if self.google.mailLast(last) else print('Failed')
				else: 
					print('No messages')
			elif prompt in AI.modes.keys():
				self.ai.start(prompt)
				print(f'switched to "{prompt}"')

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

	def guide(self):
		options = list(AI.modes.keys())
		options.remove(self.ai.mode)
		#options.remove('classificator')

		print("\nI'm '{}'{}. Switch to {}".format(self.ai.mode, ' with Functions' if self.classificator else '', str(options)))
		print("""– 'Listen': ENTER to start & stop
– 'Exit': ESC (+Enter)
- 'Functions': f
– 'Clear' conversation: 0 or # messages to keep """)
		cnt = len(self.ai.messages)-1
		if cnt:
			print("   {} messages, {} tokens".format(cnt, self.ai.tokensUsed))
		print()

	def run(self, question=None):
		if self.classificator:
			action = self.ask(question, mode='classificator')
			action = re.sub(r'[,.]', "", action.strip().lower())

			if action == 'none':
				print('Thinking')
				response = self.ask(question)

			elif action == 'communicate':
				print('Preparing mail')
				response = self.ai.chat(question, mode='messenger')
				print('Sending mail')
				self.google.mailLast({'message':response, 'mail':self.ai.me['mail']})
			else :
				response  =f'I see you are asking about "{action}". Accesing them it will be implemented later. Please be patient.'
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
	
	def enahance4screen(_, text):
		pattern = r'(?m)^\s*```([\s\S]*?)```\s*$'
		linelength = len(text.split('\n')[0])
		return re.sub(pattern, r'\n' + '–'*linelength + r'\n\1\n' + '–'*linelength + '\n', text)


class AI:
	modes = None

	def __init__(self):
		self.mode = "assistant"
		self.messages = []
		self.tokensUsed = 0

		self.loadConfig()
		self.start()
		with open('../private.key', 'r') as key:
			openai.api_key =  key.read().strip()

	def start(self, mode=None):
		self.mode = mode if mode else list(AI.modes.keys())[0]
		self.clearMessages()
		self.tokensUsed = 0
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
			rememberMessages = True
		# one time ask like for classification
		else: 
			messages = AI.modes[mode]['messages']
			rememberMessages = False

		if(question): 
			messages.append({"role": "user", "content": question})
		# if no question, ask the last one again
		elif messages: 
			messages.pop(-1)
		
		try:
			# TODO retry with openai.ChatCompletion.create(**params)
			response = openai.ChatCompletion.create(
				model = "gpt-3.5-turbo",
				messages = messages,
				#max_tokens = 1024, # TODO limit response length by this
				temperature = 0)
		except openai.error.InvalidRequestError as e:
			print (f'Limit exceeded: {e}')

		reply = response["choices"][0]["message"]["content"]
		
		# store messages if in standard chain
		if rememberMessages: 
			messages.append({"role": "assistant", "content": reply})
			self.messages = messages
			self.tokensUsed = 0
			for message in messages:
				self.tokensUsed += self.countTokens(message['content'])
		return reply

	def clearMessages(self, keep=0):
		# TODO: check for system messages and consider keeping start of the conversation after as an anchor
		if keep != 0: 
			if keep < len(self.messages):
				print([1,len(self.messages)-keep])
				try:
					self.messages = self.messages[0:1] + self.messages[-keep:]
				except IndexError:
					self.messages = AI.modes[self.mode]['messages']	
		else:
			self.messages = AI.modes[self.mode]['messages'].copy()
		


	def chatStream(self, question): # streaming returns by increments instead of the whole text at once
		self.messages.append({"role": "user", "content": question})
		response = openai.ChatCompletion.create(
			model = "gpt-3.5-turbo",
			messages = self.messages,
			temperature = 0,
			stream = True
		)
		content = ""
		for message in response:
			if "choices" in message:
				if 'content' in message["choices"][0]["delta"]:
					delta = message["choices"][0]["delta"]["content"]
					print(delta)
					content += delta
			elif "error" in message:
				print(message["error"]["message"])
			time.sleep(0.1) # not sure what time should be used not to hit rate limiting. 
		"""if content:
			self.messages.append({"role": "assistant", "content": content})"""
		return content

	def completion(self, prompt):
		response = openai.Completion.create(
			engine = "text-davinci-003",
			prompt = prompt,
			max_tokens = 1024,
			stop = None,
			temperature = 0
		)
		reply = response["choices"][0]["text"]
		return reply

	def countTokens(self, text):
		return len(re.sub(r'\s+', ' ', text).split(" "))

	def getPrice(self, text):
		return words*tokenPrice(text)

	def getLastReply(self):
		if len(self.messages)<1 or self.messages[-1]['role'] != 'assistant':
			return None
		return {
			'mail': self.me['mail'],
			'message': self.messages[-1]['content']}

	def loadConfig(self):
		conf = yaml.safe_load(open('config.yaml', 'r'))
		self.languages = " or ".join(conf['languages'])
		self.me = conf['me']
		modes = conf['modes']

		# YAML to OpenAI message format
		for m in modes:
			messages = modes[m]['messages'][0]
			role = list(messages.keys())[0]
			if m == 'classificator':
				param = modes[m]['modes']
			else:
				param = self.languages
			modes[m]['messages'] = [{'role': role, 'content': messages[role].format(param)}]
									
		AI.modes = modes
		#AI.modes = conf['modes']

	def asChatMessage(self, role, content):
		return {'role': role, 'content': content}

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