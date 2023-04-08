from ai import AI
import integrations

import yaml
import re

class Pipelines:
	def __init__(self):
		self.convert = integrations.Convertor()
		self.google = integrations.Google()
		self.classifier = None

	def execute(self, text, ai, chat):
		mode = AI.modes[ai.mode]
		pipeline = mode['pipeline'] if 'pipeline' in mode else None
		if pipeline:
			for step in pipeline:
				if step in chat.ai.modes.keys():
					text = chat.ask(text, AI(step))
				elif step == 'self':
					text = chat.ask(text)
				else:
					pipe = step.split('.')
					if len(pipe)<2 or len(pipe[0])<1:
						text = getattr(self, step)(text, chat) 
					else:
						method = getattr(self, pipe[0])
						# pipe[0] = getattr("__main__", pipe[0])
						text = getattr(method, pipe[1])(text) 
		else: 
			text = chat.ask(text)
		return str(text)

	def classify(self, question, ai, chat):
		print("…classifying ")
		if not self.classifier:
			self.classifier = AI('_classifier')
		action = chat.ask(self.convert.firstSentences(question), self.classifier)  # TODO do it singleton 
		
		# TODO do it through YAML
		if action:
			action = re.sub(r'[,.]', "", action.strip().lower())
			if 'action:' in action:
				action = action[7:].strip()
		#action = convert.yaml2json(action)

		# ask if no action
		if action in ('none', None):
			print('…thinking\n')
			response = self.execute(question, ai, chat)
			#response = self.ask(question)

		elif hasattr(self, action):
			response = getattr(self, action)(question, chat) 
		else:
			response  =f'I see you are asking about "{action}". That function will be implemented later. Please be patient.'

		return str(response)


	def translation(self, text, chat):
		text = chat.ask(text)
		json = self.convert.yaml2json(text, defaultTag='translation')
		output = json['translation']+"\n"
		try:
			output += f">>> from: {json['from']}, to: {json['to']} <<<"
			chat.ai.languages  = [json['from'], json['to']]
		except: 
			print("Error: did not classify the languages.")
		return output

	def communicate(self, question, chat): 
		print('…preparing message')
		response = chat.ask(question, AI('messenger'))
		if response:
			try:
				data = yaml.load(response, Loader=yaml.FullLoader)
				if 'Message' not in data:
					data['Message'] = response
			
			except Exception as e:
				print (e) 
				data = {'Message':response, 'Subject': 'note to myself'}

			try:
				if data['Message'] in ('this-conversation', 'last-message'):
					data['Message'] = chat.ai.messages[-1]['content']
					data['Summary'] = "Our conversation"

				response = "Sending message to: {}.\nBy: {}.\nSubject: {}.".format(data['Recipients'], data['Service'], data['Summary'])

				data['Recipients'] = chat.ai.me['mail']
				self.google.mailLast({'message':data['Message'], 'mail':chat.ai.me['mail'], 'subject':data['Summary']})
			except Exception as e:
				print("Error:")
				print(e)
			return response

	def inbox(self, question, chat):
		print('…summarizing inbox')
		time.sleep(3)
		return self.google.summarizeMailbox()

	def calendar(self, question, chat):
		print('…summarizing inbox')
		return self.google.scheduleMeeting(question)


	def write(self, question, chat):
		print('…writing text')
		response = self.ask(question, AI('_classifier'))

		response = "Here's the text:\n\n" + response + "\n\nDo you want me to send it?"

		return response


	def command(self, question, chat):
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