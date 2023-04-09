import openai

import integrations

import time
import yaml
import re

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
		except (openai.error.InvalidRequestError, openai.error.APIConnectionError, openai.error.APIError) as e:
			self.stats.add({'errors': 1}, 'whisper-1')
			print(f"Error: {type(e).__name__}: {e}")
			return False
		except Exception as e:
			# also the case of no internet
			self.stats.add({'errors': 1}, 'whisper-1')
			print(f"Error: {type(e).__name__}: {e}")
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
		if 'model' not in params:
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
		
		except (openai.error.InvalidRequestError, openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.APIConnectionError, openai.error.Timeout, openai.error.APIError) as e:
			t = time.time()-t
			self.stats.add({'errors': 1, 'time': t}, self.mode)
			return {'error': e, 'time':t}

		except Exception as e:
			t = time.time()-t
			self.stats.add({'errors': 1, 'time': t}, self.mode)
			return {'error': e, 'time':t}

		
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

	def getLastReply(self, back=0):
		i = len(self.messages)-1
		while i>=0 and back>=0:
			if self.messages[i]['role'] == 'assistant':
				if back == 0:
					return {'message': self.messages[i]['content']}
				else:
					back -= 1
			i -= 1

		return None