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
"""from rich.console import Console
console = Console()
from rich.style import Style
"""
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
		self.pipeline = Pipelines(self)
		self.services = integrations.Services()

		self.logger = integrations.Logger()
		
		self.execute = self.pipeline.execute
		self.minChars = 5

	def guide(self):
		options = list(AI.modes.keys())
		options.remove(self.ai.mode)
		options = [o for o in options if not o.startswith("_")]

		rprint("\nI'm '{}' now. I can become:\n{}".format(self.ai.mode, str(options)))

		rprint(guide.format('off' if self.execute == self.pipeline.execute else "'on'", self.ai.models[self.ai.model]))

		cnt = len(self.ai.messages)-1
		if cnt:
			rprint("   {} messages, {} tokens".format(cnt, self.ai.tokensUsed))
		print()

	def main(self): 
		self.guide()

		""" Launches functions based on user input """
		escape = '\x1b'

		while True:
			prompt = input()

			# Exit by Escape
			if prompt == escape:
				s = self.ai.stats.print()
				self.logger.log(s)
				break

			if self.rec.recording and len(prompt) == 0:
				self.transcript_recording()

			else:
				functions = {
					'<': (lambda x: (self.ai.load_config(), self.ai.clear_messages())),
					'>': self.response_to_JSON,
					'f': self.toggle_functions,
					'i': self.pipeline.improve_prompt,
					'm': self.print_messages,
					'l': (lambda x: (print("Type note to log"), self.logger.log('- note: '+input()))),
					'p': (lambda x: self.get_input(self.paste())),
					'c': self.copy_last_message_to_clipboard,
					'v': self.switch_model,
					'@': self.mail_last_message
					}
				if prompt in functions.keys():
					functions[prompt](prompt)
				
				elif prompt.isdigit() or (len(prompt)>1 and prompt[0]=='-' and prompt[1:].isdigit()):
					self.clear_messages(prompt)

				elif prompt in AI.modes.keys():
					self.switch_AI(prompt)

				else:
					self.get_input(prompt)

	def get_input(self, prompt):

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

	def toggle_functions(self, prompt=None):
		if self.execute == self.pipeline.execute: 
			self.execute = self.pipeline.classify
			status = "'on'"
		else:
			self.execute = self.pipeline.execute
			status = 'off'

		rprint("Functions {}".format(status))

	def switch_AI(self, prompt):
		self.ai = AI(prompt)
		print(f'switched to "{prompt}"')

	def switch_model(self, prompt=None):
		print(self.ai.switch_model() +' model chosen')

	def run(self, question, voice_recognized=False): 

		response = self.execute(question)
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

	def transcript_recording(self):
		file = self.rec.stop()
		print('…recognizing')
		transcript = self.ai.voice_to_text(file)
		if not transcript:
			if transcript == False:
				mess = 'Sorry the voice recognition is currently down. Please try again in a while\n'
			elif transcript == "":
				mess = "No input.\n"
			else:
				mess = "No internet. Connect it.\n"
			print(mess)
			self.say.say(mess)
			return False
		os.system('clear')
		
		text = transcript.text
		print(text+'\n'); 
		self.run(text, True)
		return text

	def ask(self, question, ai=None):
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
			self.print_blocks(self.convert.split_to_MD_blocks(response))
			#print(response)
			if say:
				self.say.say(response)
			self.guide()

	def print_blocks(_, blocks):
		for block in blocks:
			block['text'] = block['text'].replace('[', "\\[") # rich library uses that as formatting
			if block['type'] == 'code':
				rprint("——————————"+block['text'])
			else: 
				rprint(block['text'])

	def copy_last_message_to_clipboard(self, prompt=None):
		reply = self.ai.get_last_reply()
		if reply:
			text = reply['message']
			print(text)
			subprocess.Popen('pbcopy', stdin=subprocess.PIPE, universal_newlines=True).communicate(text)

	def paste(_):
		'cs_CZ.UTF-8'
		text = subprocess.check_output('pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')
		print(text)
		return text

	def clear_messages(self, keep):
		self.ai.clear_messages(int(keep))
		os.system('clear')
		print("Only last {} messages kept".format(keep) if int(keep) else "Messages cleared")
		self.guide()

	def mail_last_message(self, prompt=None):
		message = self.ai.get_last_reply()
		if message:
			mem = self.ai.memory.data
			sender = f"{mem['assistant']['name']}<{mem['assistant']['mail']}>"
			subject = message['subject'] if 'subject' in message else "Note to myself"
			if self.services.send_mail(sender, mem['me']['mail'], subject, message['message']):
				print('Sent')
			else: 
				print('Failed')

		else: 
			print('No messages')

	def print_messages(self, prompt=None):
		for i, message in enumerate(self.ai.messages):
			print(str(i) + ":")
			print(message['content'], "\n")

	def response_to_JSON(self, prompt):
		try:
			data = self.convert.yaml2json(self.ai.messages[-1]['content'])
			self.convert.save_cases(data, input("What model are the data for: "), input("Expected value or comma separated fields in that model: "))
		except Exception as e:
			print(e)


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
		#woke = r'\b(\w{3,})/á\b'
		woke = r"(\w{3,})(\/á)|(\/a)|\(\-?a\)(?=\s|$)"
		processed = re.sub(woke, r'\1', processed)
		
		return processed