import openai

import time

import sounddevice as sd
import soundfile as sf
from langdetect import detect

import os
import subprocess 
#import shlex
import re
import yaml

from rich import print
from rich.markdown import Markdown
import markdown	

import integrations

import traceback

class Chat:
	def __init__(self):
		self.rec = Recorder()
		self.say = Synthesizer()
		self.ai = AI()
		self.google = integrations.Google()

		self.logger = integrations.Logger()
		self.convertor = integrations.Convertor()

		self.classifier = None
		self.minChars = 5

	def guide(self):
		options = list(AI.modes.keys())
		options.remove(self.ai.mode)
		options = [o for o in options if not o.startswith("_")]

		print("\nI'm '{}' now. I can become:\n{}".format(self.ai.mode, str(options)))

		print("""– 'Listen': ENTER to start & stop
– 'Exit': ESC (+Enter)
- 'c'opy 'p'aste 
- 'Functions' are '{}', using {}
– 'Clear' conversation: 0 or # messages to keep """.format('on' if self.classifier else 'off', self.ai.models[self.ai.model]))


		cnt = len(self.ai.messages)-1
		if cnt:
			print("   {} messages, {} tokens".format(cnt, self.ai.tokensUsed))
		print()

	def go(self): 
		self.guide()

		while True:
			prompt = input()

			# paste prompt from clipboard
			if 'p' == prompt:
				prompt = self.pasteClipboard()
			"""elif 'r' == prompt: # retry voice reco (if it failed)
				# might be handy also to play it
				self.rec.recording = True;
				#TBD"""

			# ask by voice
			if self.rec.recording and len(prompt) == 0:
				file = self.rec.stop()
				print('…recognizing')
				transcript = self.ai.voice2text(file)
				if not transcript:
					mess = 'Sorry the voice recognition is currently down. Please try again in a while\n'
					print(mess)
					self.say.say(mess)
					continue
				os.system('clear')
				
				text = transcript.text
				print(text+'\n'); 
				self.run(text, True)


			# Exit 
			elif prompt.lower() in['\x1b', 'exit', 'esc']: # ESC
				s = self.ai.stats.print()
				self.logger.log(s)
				break

			# Service controls

			# Clear history or remove messages
			elif prompt.isdigit() or (len(prompt)>1 and prompt[0]=='-' and prompt[1:].isdigit()):
				self.ai.clearMessages(int(prompt))
				os.system('clear')
				print("Only last {} messages kept".format(prompt) if int(prompt) else "Messages cleared")
				self.guide()

			# reload config
			elif '<' == prompt:
				self.ai.loadConfig()
				self.ai.clearMessages()

			# last response to data structure
			elif '>' == prompt:
				try:
					print (self.logger.yaml2json(self.ai.messages[-1]['content']))
				except Exception as e:
					print(e)

			# toggle functions/classifier
			elif 'f' == prompt:
				if self.classifier == None: 
					self.classifier = AI('_classifier')
				else:
					self.classifier = None	

				print("Functions {}".format('on' if self.classifier else 'off'))

			# print messages
			elif 'm' == prompt:
				for message in self.ai.messages:
					print(message['content'])

			# log a comment
			elif 'l' == prompt:
				self.logger.log('- note: '+input())

			# copy reply to clipboard
			elif 'c' == prompt:
				reply = self.ai.getLastReply()
				if reply:
					self.copy2clipboard(reply['message'])

			# change model version
			elif 'v' == prompt:
				print(self.ai.switchModel() +' model chosen')

			# mail last reply
			elif '@' == prompt:
				last = self.ai.getLastReply()
				if last:
					print('Sent') if self.google.mailLast(last) else print('Failed')
				else: 
					print('No messages')

			# switch model
			elif prompt in AI.modes.keys():
				self.ai = AI(prompt)
				print(f'switched to "{prompt}"')

			# ask by text prompt
			else:
				# repeat last question
				if 're' == prompt: #repeating question
					self.run()
				
				# multiline input
				elif prompt and '\\' == prompt[-1]:
					enterCount = 0
					while enterCount <= 1:
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

	def run(self, question, voice_reco=False):
		if not question:
			print('repeating not implemented yet')
			return None

		if self.classifier:
			print("…classifying ")

			# classify only start not to confuse him to much
			firstSentences = re.split(r'(?<=\w[.?^!]) +(?=\w)', question)
			firstSentences = ".".join(firstSentences[:2])
			if len(firstSentences)<200:
				firstSentences = question[:200]
			
			action = self.ask(firstSentences, self.classifier) 

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
				response = self.ask(question, AI('messenger'))
				if response:
					try:
						data = yaml.load(response, Loader=yaml.FullLoader)
						if 'Body' not in data:
							data['Body'] = response
					
					except Exception as e:
						print (e) 
						data = {'Body':message, 'Subject': 'note to myself'}

					if data['Body'] in ('this-conversation', 'last-message'):
						data['Body'] = self.ai.messages[-1]['content']
						data['Subject'] = "Our conversation"

					response = "Sending message to: {}.\nBy: {}.\nSubject: {}.".format(data['Recipient'], data['Service'], data['Subject'])

					data['Recipient'] = self.ai.me['mail']
					self.google.mailLast({'message':data['Body'], 'mail':self.ai.me['mail'], 'subject':data['Subject']})

			elif 'inbox' == action:
				print('…summarizing inbox')
				time.sleep(3)
				response = self.google.summarizeMailbox()

			elif 'calendar' == action:
				response = self.google.scheduleMeeting(question)

			elif 'write' == action:
				print('…writing text')
				response = self.ask(question, AI('_classifier'))

				response = "Here's the text:\n\n" + response + "\n\nDo you want me to send it?"

			elif 'command' == action:
				response = None
				#pattern = [['become, be', 'work'], ['my', 'a', 'as', None]]
				first_word = re.findall(r'\w+', question)[0].lower()
				try:
					if first_word in ('become', 'be'):
						last_word = re.findall(r'\w+', question)[-1].lower()
						modes = AI.modes.keys()

						if last_word in modes:
							response = f"Now I'm {last_word}"
							# ai = AI(last_word) TODO
						else:
							response = f"Sorry, I can't be '{last_word}' yet"
				except:
					pass

				if not response:
					response = self.ask(question)

				#if re.search(r"\b(?:become my|be my)\s+(\w+)\b", question.strip()): mode = match.group(1).strip()

			else:
				response  =f'I see you are asking about "{action}". That function will be implemented later. Please be patient.'
		else:
			print('…thinking\n')
			response = self.ask(question)
			
		self.reply(response)

		# log stats (time, length)
		try:
			s = []
			times = self.ai.stats.last
			if(voice_reco):
				s.append(times['whisper-1']['time'])
			if self.classifier:
				s.append(times[self.classifier.mode]['time'])
			s.append(times[self.ai.mode]['time'])
		except Exception:
			pass

		#print(str(round(sum(s),1)) + "s = "+ " + ".join(map(lambda x: str(round(x, 1))+"s", s)))
		return response

	def reply(self, response, say=True):
		if response:
			"""json = self.logger.yamlize(response)
			if(json):
				response = json"""
			print(self.enhance4screen(response))			
			if say:
				"""try: 
					json = self.logger.yamlize(response)
					if 'Translation' in json: 
						response = json['Translation']
					elif 'translation' in json: 
						response = json['translation']
				except:
					pass"""
		
				self.say.say(response)
			self.guide()

	def ask(self, question=None, ai=None):
		if question and len(question) < self.minChars:
			return question + ' is not a question'
		
		if ai == None:
			ai = self.ai
			self.logger.log('- |\n  '+question.replace('\n', '\n  '))

		response = ai.chat(question)
		
		if 'choices' in response:
			reply = response['choices'][0]['message']['content']
			#return reply
			try:
				mode = AI.modes[self.ai.mode]

				pipeline = mode['pipeline'] if ('pipeline' in mode) else None
				defaultTag = mode['defaultTag'] if ('defaultTag' in mode) else None
				if pipeline:
					output = getattr(self.convertor, pipeline)(reply, defaultTag) 
					#output = self.convertor.yaml2json(reply)
					return output
			except Exception as e:
				print(e)

			return reply
		else:
			if 'error' in response:
				mess = str(response['error'])
				if mess:
					print(mess)
					self.say.say(mess)
				self.logger.log('- error: '+mess+ '\n')

			#if 'traceback' in response:
			#	print(response['traceback'])
			
			return None
		
	
	def enhance4screen(_, text):
		pattern = r'(?m)^\s*```([\s\S]*?)```\s*$'
		#linelength = len(text.split('\n')[0])
		linelength = 10
		text = re.sub(pattern, r'\n' + '–'*linelength + r'\n\1\n' + '–'*linelength + '\n', text)
		#text = Markdown(text)
		return text

	def copy2clipboard(self, text):
		print(text)
		subprocess.Popen('pbcopy', stdin=subprocess.PIPE, universal_newlines=True).communicate(text)
		self.pasteClipboard()

	def pasteClipboard(_):
		'cs_CZ.UTF-8'
		text = subprocess.check_output('pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')
		print(text)
		return text

class Controller:
	def __init__(self):
		self.convertor = Convertor()

	def nurse(self, text):
		return text

	def translation(self, text):
		return self.convertor.translation(text)

class AI:
	modes = None
	conf = None
	models = ['gpt-3.5-turbo', 'gpt-4']
	key = None

	def __init__(self, mode=None, model=0):
		self.model = model
		self.messages = []
		self.tokensUsed = 0

		self.stats = integrations.Stats()
		
		# alternatively openai.api_key = os.environ.get('OPENAI_KEY')
		if not AI.key:
			with open('../private.key', 'r') as key:	# TODO read just once
				AI.key = key.read().strip()
		openai.api_key =  AI.key

		if not AI.conf:
			self.loadConfig()

		self.mode = mode if mode else list(AI.modes.keys())[0]

		# TODO should be in user storage instead of conf
		self.languages = AI.conf['languages']
		self.me = AI.conf['me']

		self.clearMessages()
		

	def loadConfig(self):
		with open('config.yaml', 'r') as file:
			AI.conf = yaml.safe_load(file)
		AI.modes = AI.conf['modes']

	def switchModel(self):
		self.model = (self.model+1)%len(self.models)
		return AI.models[self.model]

	def voice2text(self, filename):
		audio_file= open(filename, "rb")
		try:
			t = time.time()
			transcript = openai.Audio.transcribe("whisper-1", audio_file)
			t = time.time()-t

			self.stats.add({'items': 1, 'time': t, 'len': len(transcript.text)}, 'whisper-1')
		except (openai.error.InvalidRequestError, openai.error.APIConnectionError, openai.error.APIError, Exception):
			self.stats.add({'errors': 1}, 'whisper-1')
			return None
		return transcript

	def chat(self, question): 
		self.keepLastMessages()

		messages = self.messages
		if(question):
			messages.append(self.messageFromTemplate('user', question))
		
		if 'model_params' in AI.modes[self.mode]:
			params = AI.modes[self.mode]['model_params'].copy()
		else:
			params = {}
		params['model'] = AI.models[self.model]
		params['messages'] = messages


		if 'logit_bias' in params: 	# TODO words must be converted to integer tokens
			params.pop('logit_bias')
			
		t = time.time()
		try:
			
			# TODO retry with openai.ChatCompletion.create(**params)
			
			response = openai.ChatCompletion.create(**params)

			t = time.time()-t
			usage = response['usage']
			usage['time'] = t
			usage['items'] = len(response['choices'])
			self.stats.add(usage, self.mode)
		
		except (openai.error.InvalidRequestError, openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.APIConnectionError, openai.error.Timeout) as e:
			t = time.time()-t
			self.stats.add({'errors': 1, 'time': t}, self.mode)
			return {'error': e, 'traceback': traceback.format_exc(), 'time':t}
		
		messages.append(self.messageFromTemplate('assistant', response['choices'][0]['message']['content']))
		
		self.messages = messages
		self.tokensUsed = response['usage']['total_tokens']

		return response

	def messageFromTemplate(self, role, content): # TODO yet to be finished by refactoring loadConf
		templates = AI.modes[self.mode]['messages']
		
		if role in templates:
			if content:
				if isinstance(content, list):
					message = templates[role].format(*content)
				else: 
					message = templates[role].format(content)
			else:
				message = template[role].copy()
		else:
			message = content
		
		return {'role': role, 'content': message };

	def keepLastMessages(self, keep=None):
		try:
			if not keep:
				keep = AI.modes[self.mode]['messages']['remember']

			self.clearMessages(keep)
		except:
			pass
		# self.messages = messages

	def clearMessages(self, keep=0):
		# TODO: check for system messages and consider keeping start of the conversation after as an anchor
		if keep <= len(self.messages):
			try:
				# keep last messages
				if keep > 0:
					self.messages = self.messages[len(self.messages)-keep:]				
				# remove last message 
				elif keep < 0:
					if len(self.messages) > 1:
						self.messages.pop() # TODO allow more messages and self.countTokens(last message)
				#erase all
				else:
					self.tokensUsed = 0
					self.messages = []

				# TODO count tokens
			except IndexError:
				pass
		try:
			if len(self.messages)==0 or self.messages[0]['role'] != 'system':
				self.messages = [self.messageFromTemplate('system', [", ".join(self.languages)])] + self.messages;
		except Exception as e:
			print(e)

	def chatStream(self, question): # streaming returns by increments instead of the whole text at once
		self.messages.append(self.messageFromTemplate('user', question))
		response = openai.ChatCompletion.create(
			model = AI.models[self.model],
			messages = self.messages,
			temperature = 0,
			stream = True
		)
		content = ""
		for message in response:
			if 'choices' in message:
				if 'content' in message['choices'][0]['delta']:
					delta = message['choices'][0]['delta']['content']
					print(delta)
					content += delta
			elif "error" in message:
				print(message["error"]['message'])
			time.sleep(0.1) # not sure what time should be used not to hit rate limiting. 
		"""if content:
			self.messages.append({'role': "assistant", 'content': content})"""
		return content

	def completion(self, prompt):
		response = openai.Completion.create(
			engine = 'text-davinci-003',
			prompt = prompt,
			max_tokens = 1024,
			stop = None,
			temperature = 0
		)
		reply = response['choices'][0]["text"]
		return reply

	def countTokens(self, text):
		# experimentally getting ~0.7-0.75 words/tokens
		return len(re.sub(r'\s+', ' ', text).split(" "))

	def getPrice(self, text):
		return words*tokenPrice(text)

	def getLastReply(self):
		if len(self.messages)<1 or self.messages[-1]['role'] != 'assistant':
			return None
		return {
			'mail': self.me['mail'],
			'message': self.messages[-1]['content']}

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
			'en': {'name': 'Serena (Premium)', 'lang':'English', 'speed': 190}, #220
			'cs': {'name': 'Zuzana (Premium)', 'lang':'Czech', 'speed': 200}} #240, magi:190

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
		self.process = subprocess.Popen(["say", "-v", voice['name'], text, "-r", str(voice['speed'])])
		#os.system(f'say -v "{text_voice}"  "{text}"')

		return self.process

	def stop(self):
		if self.process: 
			self.process.kill()
			self.process = None

	def escape4shell(self, text): 
		""" # Popen does not seem to escape characters that disturb shell command: `"'$! anymore
		text = shlex.quote(text) 
		if text[-1]=="'":
			text = text[:-1]"""
		# shell considers starting '-' as a parameter
		if text[0]=="-": 
			text = "\\"+text
		return text
		

	def simply2read(self, text): 
		#text = text.replace("\r", "")
		
		# remove code blocks
		text = re.compile(r"(```.*?```)", re.DOTALL).sub("Example code.\n", text)

		# remove what my pipelines commented out
		text = re.compile(r"(>>>.*?<<<)", re.DOTALL).sub("", text)
		
		
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

		# unwoke
		processed = re.sub(r'\b(\w{3,})/á\b', r'\1', processed)
				
		return processed