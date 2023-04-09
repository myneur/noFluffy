from ai import AI
import integrations

import yaml
import re

import traceback

class Pipelines:
	def __init__(self, chat):
		self.convert = integrations.Convertor()
		self.google = integrations.Google()
		self.classifier = None
		self.chat = chat

	def execute(self, text, mode=None):
		chat = self.chat
		if not mode:
			mode = AI.modes[chat.ai.mode]
		pipeline = mode['pipeline'] if 'pipeline' in mode else None
		print('…thinking\n')
		if pipeline:
			for step in pipeline:
				if step in chat.ai.modes.keys():
					text = chat.ask(text, AI(step))
				elif step == 'self':
					text = chat.ask(text)
				else:
					pipe = step.split('.')
					if len(pipe)<2 or len(pipe[0])<1:
						text = getattr(self, step)(text) 
					else:
						method = getattr(self, pipe[0])
						# pipe[0] = getattr("__main__", pipe[0])
						text = getattr(method, pipe[1])(text) 
		else: 
			text = chat.ask(text)
		return str(text)

	def classify(self, question):
		print("…classifying ")
		if not self.classifier:
			self.classifier = AI('_classifier')
		action = self.chat.ask(self.convert.firstSentences(question), self.classifier)  # TODO do it singleton 
		
		# TODO do it through YAML
		if action:
			action = re.sub(r'[,.]', "", action.strip().lower())
			if 'action:' in action:
				action = action[7:].strip()
		#action = convert.yaml2json(action)

		# ask if no action
		if action in ('none', None):
			response = self.execute(question)
			#response = self.ask(question)

		elif hasattr(self, action):
			response = getattr(self, action)(question) 
		else:
			response  =f'I see you are asking about "{action}". That function will be implemented later. Please be patient.'

		return str(response)


	def translation(self, text):
		text = self.chat.ask(text)
		json = self.convert.yaml2json(text, defaultTag='translation')
		output = json['translation']+"\n"
		try:
			output += f">>> from: {json['from']}, to: {json['to']} <<<"
			self.chat.ai.languages  = [json['from'], json['to']]
		except: 
			print("Error: did not classify the languages.")
		return output

	def send_it(self, question): 
		print('…preparing message')
		chat = self.chat
		response = chat.ask(question, AI('messenger'))
		if response:
			try:
				data = self.convert.yaml2json(response)
				if 'message' not in data:
					data['message'] = response
			
			except Exception as e:
				print (e) 
				data = {'message':response, 'subject': 'note to myself'}

			try:
				data['recipients'] = chat.ai.me['mail']


				if data['message'] in ('this-conversation', 'last-message'):
					data['message'] = chat.ai.getLastReply()['message']

				try:
					summary = chat.ask(data['message'], AI('summarize'))
					data['summary'] = summary if summary else "Our last conversation"
					response = "Sending message to: {}.\nBy: {}.\nSubject: {}.".format(data['recipients'], data['service'], data['summary'])

					self.google.mailLast({'message': data['message'], 'mail': data['recipients'], 'subject': data['summary']})
				except Exception as e:
					print(f"Error: {type(e).__name__}: {e}, {e.args} ")
					traceback.print_exc()
					#print(data)

			except Exception as e:
				print("Error in creating the message. Needs review:(")
			return response

	def inbox(self, question):
		print('…summarizing inbox')
		time.sleep(3)
		return self.google.summarizeMailbox()

	def calendar(self, question):
		print('…summarizing inbox')
		return self.google.scheduleMeeting(question)


	def write(self, question):
		print('…writing text')
		response = self.ask(question, AI('_classifier'))

		response = "Here's the text:\n\n" + response + "\n\nDo you want me to send it?"

		return response


	def command(self, question):
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