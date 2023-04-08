from ai import AI

import time

import sounddevice as sd
import soundfile as sf
from langdetect import detect

import os
import subprocess 
#import shlex
import re
import yaml

from rich import print as rprint
from rich.markdown import Markdown
import markdown	

import integrations
from pipelines import Pipelines

import traceback

guide = """– 'Listen': ENTER to start & stop
– 'Exit': ESC (+Enter)
- 'Functions' are {}, using {}
– 'Clear' conversation: 0 """

class Chat:
	def __init__(self):
		self.rec = Recorder()
		self.say = Synthesizer()
		self.ai = AI()
		self.convert = integrations.Convertor()
		self.pipeline = Pipelines()
		self.google = integrations.Google()

		self.logger = integrations.Logger()
		
		self.classifier = None
		self.minChars = 5

	def guide(self):
		options = list(AI.modes.keys())
		options.remove(self.ai.mode)
		options = [o for o in options if not o.startswith("_")]

		rprint("\nI'm '{}' now. I can become:\n{}".format(self.ai.mode, str(options)))

		rprint(guide.format("'on'" if self.classifier else 'off', self.ai.models[self.ai.model]))

		cnt = len(self.ai.messages)-1
		if cnt:
			rprint("   {} messages, {} tokens".format(cnt, self.ai.tokensUsed))
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
					if transcript == False:
						mess = 'Sorry the voice recognition is currently down. Please try again in a while\n'
					elif transcript == "":
						mess = "No input.\n"
					else:
						mess = "No internet. Connect it.\n"
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
			elif prompt.startswith('>'): # >model>value
				try:
					data = self.convert.yaml2json(self.ai.messages[-1]['content'])
					print(data)
					groups = prompt.split('>')
					if len(groups)>2:
						self.convert.saveAsCases(data, groups[1].strip(), groups[2].strip())
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

	def run(self, question, voice_recognized=False): 
		if not question:
			print('No input.')
			self.say.say("No input given")
			return None

		if self.classifier:
			print("…classifying ")

			action = self.ask(self.convert.firstSentences(question), self.classifier) 

			# be tolerant in detecting action
			if action:
				action = re.sub(r'[,.]', "", action.strip().lower())
				if 'action:' in action:
					action = action[7:].strip()

			# ask if no action
			if action in ('none', None):
				print('…thinking\n')
				response = self.ask(question)

			# run prompt corresponding with the action that was classified
			elif hasattr(self.pipeline, action):
				response = getattr(self.pipeline, action)(question, self) 

			else:
				response  =f'I see you are asking about "{action}". That function will be implemented later. Please be patient.'
		else:
			print('…thinking\n')
			response = self.pipeline.execute(question, self.ai, self)
			#response = self.ask(question)
			
		self.reply(response)

		# log stats (time, length)
		try:
			s = []
			times = self.ai.stats.last
			if voice_recognized:
				s.append(times['whisper-1']['time'])
			if self.classifier:
				s.append(times[self.classifier.mode]['time'])
			s.append(times[self.ai.mode]['time'])
		except Exception:
			pass

		#print(str(round(sum(s),1)) + "s = "+ " + ".join(map(lambda x: str(round(x, 1))+"s", s)))
		return response

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
		
	def reply(self, response, say=True):
		if response:
			rprint(self.enhance4screen(response))			
			if say:
				self.say.say(response)
			self.guide()

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