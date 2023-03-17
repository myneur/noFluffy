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

		self.classify = True
		self.minChars = 5

	def go(self): 
		self.guide()

		while True:
			prompt = input()

			# ask by voice
			if self.rec.recording and len(prompt) == 0:
				file = self.rec.stop()
				print('…recognizing')
				text = self.ai.voice2text(file)
				if not text:
					mess = 'Sorry the voice recognition is currently down. Please try again in a while\n'
					print(mess)
					self.say.say(mess)
					continue
				os.system('clear')
				print(text); print()
				self.run(text)

			# Service controls
			elif prompt.lower() in['\x1b', 'exit', 'esc']: # ESC
				break
			elif prompt.isdigit():
				self.ai.clearMessages(int(prompt))
				os.system('clear')
				print("Only last {} messages kept".format(prompt) if int(prompt) else "Messages cleared")
				self.guide()
			elif '<' == prompt:
				self.ai.loadConfig()
			elif 'f' == prompt:
				self.classify = not self.classify
				print(f'Functions: {self.classify}')
			elif 'm' == prompt:
				for message in self.ai.messages:
					print(message['content'])
			elif 'v' == prompt:
				print(self.ai.switchModel() +' model chosen')
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
				
				# multiline input
				elif prompt and '\\' == prompt[-1]:
					enterCount = 0
					while enterCount <= 2:
						line = input()
						prompt += '\n'+ line;
						if line == '':
							enterCount += 1
						else:
							enterCount = 0

					self.run(prompt)

				# single line input
				elif len(prompt) >= self.minChars:
					self.run(prompt)
				
				# start listening when he hit just the enter and no other request detected
				else:
					print('Speak!\r\nENTER to get reply!')
					self.say.stop()
					self.rec.rec()


	def guide(self):
		options = list(AI.modes.keys())
		options.remove(self.ai.mode)
		options = [o for o in options if not o.startswith("_")]

		print("\nI'm '{}'{}. Switch to {}".format(self.ai.mode, ' with Functions' if self.classify else '', str(options)))
		print("""– 'Listen': ENTER to start & stop
– 'Exit': ESC (+Enter)
- 'Functions': f
– 'Clear' conversation: 0 or # messages to keep """)
		cnt = len(self.ai.messages)-1
		if cnt:
			print("   {} messages, {} tokens".format(cnt, self.ai.tokensUsed))
		print()

	def run(self, question):
		if not question:
			return None

		if self.classify:
			print("…classifying ")

			# classify only start not to confuse him to much
			firstSentences = re.split(r'(?<=\w[.?^!]) +(?=\w)', question)
			firstSentences = ".".join(firstSentences[:2])
			if len(firstSentences)<200:
				firstSentences = question[:200]
			
			action = self.ask(firstSentences, mode='_classifier') 

			# run prompt corresponding with the action that was classified
			if action:
				action = re.sub(r'[,.]', "", action.strip().lower())

			if 'action:' in action:
				action = action[7:].strip()

			if action in ('none', None):
				print('…thinking\n')
				response = self.ask(question)

			elif 'communicate' == action:
				print('…preparing message')
				response = self.ai.chat(question, mode='messenger')
				try:
					data = yaml.load(response, Loader=yaml.FullLoader)
					if 'Body' not in data:
						data['Body'] = response
				except Exception as e:
					print (e) 
					data = {'Body':message, 'Subject': 'note to myself'}

				if data['Body'] in ('this-conversation', 'last-message'):
					data['Body'] = self.ai.messages[-1]['content']
					data['Subject'] = "Our last conversation"

				response = "Sending message to: {}.\nBy: {}.\nSubject: {}.".format(data['Recipient'], data['Service'], data['Subject'])

				data['Recipient'] = self.ai.me['mail']
				self.google.mailLast({'message':data['Body'], 'mail':self.ai.me['mail'], 'subject':data['Subject']})

			else :
				response  =f'I see you are asking about "{action}". That function will be implemented later. Please be patient.'
		else:
			response = self.ask(question)
			
		self.reply(response)
		return response

	def reply(self, response, say=True):
		print(self.enahance4screen(response))			
		if say:
			self.say.say(response)
		self.guide()

	def ask(self, question=None, mode=None):
		if question and len(question) < self.minChars:
			return question + ' is not a question'
		return self.ai.chat(question, mode)
	
	def enahance4screen(_, text):
		pattern = r'(?m)^\s*```([\s\S]*?)```\s*$'
		linelength = len(text.split('\n')[0])
		return re.sub(pattern, r'\n' + '–'*linelength + r'\n\1\n' + '–'*linelength + '\n', text)

class AI:
	modes = None
	models = ['gpt-3.5-turbo', 'gpt-4']

	def __init__(self, model=0):
		self.model = model
		self.mode = "assistant"
		self.messages = []
		self.tokensUsed = 0

		self.loadConfig()
		self.start()
		with open('../private.key', 'r') as key:
			openai.api_key =  key.read().strip()

	def switchModel(self):
		self.model = (self.model+1)%len(self.models)
		return AI.models[self.model]

	def start(self, mode=None):
		self.mode = mode if mode else list(AI.modes.keys())[0]
		self.clearMessages()
		self.tokensUsed = 0
		return self.mode	

	def voice2text(self, filename):
		audio_file= open(filename, "rb")
		try:
			transcript = openai.Audio.transcribe("whisper-1", audio_file)
		except (openai.error.InvalidRequestError, openai.error.APIConnectionError):
			return None
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
			messages.append({"role": "user", "content": AI.modes[mode]['template'].format(question)})

		# if no question, ask the last one again
		elif messages and messages[-1]['role'] == 'assistant': 
			messages.pop(-1)
		else:
			return None
		
		try:
			# TODO retry with openai.ChatCompletion.create(**params)
			response = openai.ChatCompletion.create(
				model = AI.models[self.model],
				messages = messages,
				#max_tokens = 1024, # TODO limit response length by this
				temperature = 0)
		except (openai.error.InvalidRequestError, openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.APIConnectionError) as e:
			print(e)
			return None
		except openai.error.Timeout as e:
			print (f'Limit exceeded: {e}')
			return None

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
				try:
					self.messages = self.messages[0:1] + self.messages[-keep:]
				except IndexError:
					self.messages = AI.modes[self.mode]['messages']	
		else:
			self.messages = AI.modes[self.mode]['messages'].copy()
		


	def chatStream(self, question): # streaming returns by increments instead of the whole text at once
		self.messages.append({"role": "user", "content": question})
		response = openai.ChatCompletion.create(
			model = AI.models[self.model],
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
			engine = 'text-davinci-003',
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
		self.languages = conf['languages']
		self.me = conf['me']
		modes = conf['modes']

		# YAML to OpenAI message format
		for m in modes:
			# TODO generalize
			params = [" or ".join(self.languages)]
			
			messages = modes[m]['messages']
			modes[m]['messages'] = [{'role': 'system', 'content': messages['system'].format(*params)}]
			modes[m]['template'] = messages['user']
									
		AI.modes = modes

	def asChatMessage(self, role, content):
		return {'role': role, 'content': content}

class Recorder:
	def __init__(self):
		self.format = 'mp3'
		self.sample_rate = 44100
		self.file = "/tmp/ch.sl8.jewel."+self.format
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
			'en': {'name': 'Serena (Premium)', 'lang':'English', 'speed': 220},
			'cs': {'name': 'Zuzana (Premium)', 'lang':'Czech', 'speed': 240}}
		self.process = None

	def say(self, text, lang=None):
		try:
			if not lang:
				lang = detect(text[:100])
			voice = self.voices[lang]
		except:
			lang = list(self.voices.keys())[0]
			voice = self.voices[lang]

		text = self.escape4shell(self.simply2read(text))

		#os.system(f'say -v "{text_voice}"  "{text}"')
		self.process = subprocess.Popen(["say", "-v", voice['name'], text, "-r", str(voice['speed'])])
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