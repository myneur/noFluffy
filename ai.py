import openai
import os
#from openai.embeddings_utils import cosine_similarity
#from openai.datalib import numpy as np
import tiktoken
from unidecode import unidecode

from integrations import Stats, Memory

import time
import yaml
import re

class AI:
	modes = None
	conf = None
	models = ['gpt-4o-mini', 'gpt-4o']
	key = None
	#organization = None
	#client = None

	def __init__(self, mode=None, model=0):
		self.model = model
		self.messages = []
		self.tokensUsed = 0
		self.lastUsedTime = 0
		self.refreshAfter = 5*60

		self.set_limit()

		self.stats = Stats()
		
		if not AI.key:
			AI.key = os.environ.get('OPENAI_API_KEY')
			#AI.organization = os.environ.get('OPENAI_ORGANIZATION_ID')
			if not AI.key:
				with open('../private.key', 'r') as key:	# TODO read just once
					AI.key = key.read().strip()
		
		self.ensureAPIConnection()

		if not AI.conf:
			self.load_config()

		self.mode = mode if mode else list(AI.modes.keys())[0]

		self.memory = Memory() # structured information 
		self.cache = Memory('cache') # for expensive operations like embeddings

		self.clear_messages()

	def set_limit(self, limit=None):
		if limit:
			self.limit = limit
			return 
		try:
			self.limit = self.conf['model']['chat'][self.model]['limit']
		except:
			self.limit = 2000
			return
		
	def ensureAPIConnection(self):
		""" After hours of inactivity it typically fails: trying to debug how to make it robust: """
		t = time.time()
		if self.refreshAfter < t - self.lastUsedTime:
			openai.api_key = AI.key # TODO will it really work? Can we depart from it? 
			#self.client = openai.OpenAI(organization=self.organization) # TODO move to using 
		self.lastUsedTime = t

	def load_config(self):
		with open('data/config.yaml', 'r') as file:
			AI.conf = yaml.safe_load(file)
		AI.modes = AI.conf['modes']

	def switch_model(self):
		self.model = (self.model+1)%len(self.models)
		self.set_limit()
		return AI.models[self.model]

	def voice_to_text(self, filename):
		audio_file= open(filename, "rb")
		self.ensureAPIConnection()
		try:
			t = time.time()
			transcript = openai.Audio.transcribe("whisper-1", audio_file)
			t = time.time()-t

			self.stats.add({'items': 1, 'time': t, 'len': len(transcript.text)}, 'whisper-1')
		except openai.error.APIConnectionError as e:
			print("The AI is tired. Waiting 5 seconds… (APIConnectionError)")
			time.sleep(5)
			print(f"Error: {type(e).__name__}: {e}")
			print(str(e))
			print(e.args)
			print(e.__traceback__)
			print(e.__cause__)
			print(e.__context__)

			return self.voice_to_text(filename)
		except (openai.error.InvalidRequestError, openai.error.APIError) as e:
			self.stats.add({'errors': 1}, 'whisper-1')
			print(f"Error: {type(e).__name__}: {e}")
			return False
		except Exception as e:
			# also the case of no internet
			self.stats.add({'errors': 1}, 'whisper-1')
			print(f"Error: {type(e).__name__}: {e}")
			return None

		return transcript

	def text_to_voice(self, text):
		#speech_file_path = self.file = "/tmp/ch.sl8.jewel.mp3" #Path(__file__).parent / "speech.mp3"
		response = openai.audio.speech.create(
		  model="tts-1", # tts-1, tts-1-hd
		  voice="alloy", #alloy, echo, fable, onyx, nova, and shimme
		  #speed=1.0,
		  #response_format=mp3 #mp3, opus, aac, flac
		  input=text
		)
		#response.stream_to_file(speech_file_path)
		return response #.content for byte stream

	def chat(self, question): 
		self.keep_last_messages()
		self.ensure_limits(question)

		messages = self.messages
		if(question):
			messages.append(self.message_from_template('user', question))
		
		if 'model_params' in AI.modes[self.mode]:
			params = AI.modes[self.mode]['model_params'].copy()
		else:
			params = {}
		if 'model' not in params:
			params['model'] = AI.models[self.model]
		params['messages'] = messages

		if 'logit_bias' in params: 	# TODO words must be converted to integer tokens
			params.pop('logit_bias')
			
		self.ensureAPIConnection()
			
		t = time.time()

		try:
			
			# TODO retry with openai.ChatCompletion.create(**params)
			
			response = openai.ChatCompletion.create(**params)

			t = time.time()-t
			usage = response['usage']
			usage['time'] = t
			usage['items'] = len(response['choices'])
			self.stats.add(usage, self.mode)
		
		except (openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.APIConnectionError, openai.error.Timeout, openai.error.APIError) as e:
			print("Error: ", f"The AI is tired. Waiting 5 seconds… ({type(e).__name__})")
			time.sleep(5)
			return self.chat(question)

		except openai.error.InvalidRequestError as e:
			if str(e).startswith("This model's maximum context length is"): 
				self.ensure_limits(question, int(self.limit/2))
				self.chat(question)
			t = time.time()-t
			self.stats.add({'errors': 1, 'time': t}, self.mode)
			return {'error': f"Error: {type(e).__name__}: {e}", 'time':t}

		except Exception as e:
			t = time.time()-t
			self.stats.add({'errors': 1, 'time': t}, self.mode)
			return {'error': f"Error: {type(e).__name__}: {e}", 'time':t}

		self.tokensUsed = response['usage']['total_tokens']
		messages.append(self.message_from_template('assistant', response['choices'][0]['message']['content']))
		
		self.messages = messages
		return response

	def message_from_template(self, role, content): 
		templates = AI.modes[self.mode]['messages']
		
		# mem = self.memory.data
		# TODO eval(f"f'''{template}'''")

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
		
		return {'role': role, 'content': message};

	def keep_last_messages(self, keep=None):
		try:
			if not keep:
				keep = AI.modes[self.mode]['messages']['remember']

			self.clear_messages(keep)
		except:
			pass
		# self.messages = messages
		return len(self.messages)

	def add_message(self, text, role='assistant'):
		try:
			self.tokensUsed += self.count_tokens(text)
			self.messages.append(self.message_from_template(role, text))
		except Exception as e:
			print(f"Failed adding message to memory: {type(e).__name__}: {e}")

	def clear_messages(self, keep=0):
		# TODO: check for system messages and consider keeping start of the conversation after as an anchor
		if keep <= len(self.messages):
			try:
				# keep last messages
				if keep > 0:
					self.messages = self.messages[len(self.messages)-keep:]				
				# remove last message 
				elif keep < 0:
					if len(self.messages) > 1:
						self.messages.pop() # TODO allow more messages and self.count_tokens(last message)
				#erase all
				else:
					self.tokensUsed = 0
					self.messages = []

				# TODO count tokens
			except IndexError:
				pass
		try:
			if len(self.messages)==0 or self.messages[0]['role'] != 'system':
				if len(self.messages)>0:
					self.messages = self.messages[1:]
				self.messages = [self.message_from_template('system', [", ".join(self.memory.data['languages'])])] + self.messages;
		except Exception as e:
			print(f"Error: {type(e).__name__}: {e}")
		return len(self.messages)

	def ensure_limits(self, text="", limit=None, expected_reply=300):
		if limit == None: 
			limit = self.limit

		expected_addition = expected_reply + self.count_tokens(text)
		expected = self.tokensUsed + expected_addition
		mess_len = 0
		while limit < expected and mess_len != len(self.messages):
			mess_len = len(self.messages)
			self.clear_messages(mess_len-1)
			self.tokensUsed = self.count_tokens()
			expected = self.tokensUsed + expected_addition
		return self.tokensUsed

	def stream_chat(self, question): # streaming returns by increments instead of the whole text at once
		self.messages.append(self.message_from_template('user', question))
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

	def embeddings(self, text, model='text-embedding-ada-002'):
		if type(text) is not list:
			text = text.replace("\n", " ")
			text = re.findall(r'\b\w+\b', text)
		if model not in self.cache.data:
			self.cache.data[model] = {}
		
		tuhash = hash(tuple(text))
		if tuhash in self.cache.data[model]: 
			embs = self.cache.data[model][tuhash] 
		else:
			embs = openai.Embedding.create(input = text, model=model)['data'][0]['embedding']
			self.cache.data[model][tuhash] = embs
		return embs

	def find_similar(self, items, filters, threshold=0.88):
		""" returns the most similar item from the array of dictionaries to the values of the dictionary, e. g. {'name': "Mařena"} """

		preprocess = lambda x: self.embeddings(unidecode(x).lower())
		filters = {key: preprocess(value) for key, value in filters.items()}

		matches = []
		for i, it in enumerate(items):
			#print('.', end='')
			print('.')
			for k in filters.keys():
				embs = preprocess(it[k])
				similar = self.similarity(embs, filters[k]) 
				items[i]['similarity'] = similar
				if similar > threshold:
					matches.append(it)
		sorted_matches = sorted(matches, key=lambda k: k['similarity'], reverse=True)
		return sorted_matches
	
	def similarity(_, a, b):
	    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
				
	def count_tokens(self, text=None, encoding_name='cl100k_base'):
		encoding = tiktoken.get_encoding(encoding_name)
		if text:
			num_tokens = len(encoding.encode(text))
		else:
			num_tokens = sum(self.count_tokens(m['content']) for m in self.messages)
		#num_tokens = (int(1.4 * len(re.sub(r'\s+', ' ', text).split(" "))))
		return num_tokens

	def cut_to_tokens(self, text, limit):
		return ''.join(re.findall(r'\S+\s*', text)[:int(limit*.75)])

	def get_last_reply(self, back=0):
		i = len(self.messages)-1
		while i>=0 and back>=0:
			if self.messages[i]['role'] == 'assistant':
				if back == 0:
					return {'message': self.messages[i]['content']}
				else:
					back -= 1
			i -= 1

		return None