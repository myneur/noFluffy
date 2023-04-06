from ai import AI
import integrations

import yaml
import re

class Pipelines:
	def __init__(self):
		self.convertor = integrations.Convertor()
		self.google = integrations.Google()

	def translation(self, text):
		return self.convertor.translation(text)

	def communicate(self, question, chat): 
		print('…preparing message')
		response = chat.ask(question, AI('messenger'))
		if response:
			try:
				data = yaml.load(response, Loader=yaml.FullLoader)
				if 'Body' not in data:
					data['Body'] = response
			
			except Exception as e:
				print (e) 
				data = {'Body':message, 'Subject': 'note to myself'}

			try:
				if data['Body'] in ('this-conversation', 'last-message'):
					data['Body'] = chat.ai.messages[-1]['content']
					data['Summary'] = "Our conversation"

				response = "Sending message to: {}.\nBy: {}.\nSubject: {}.".format(data['Recipients'], data['Service'], data['Summary'])

				data['Recipients'] = chat.ai.me['mail']
				self.google.mailLast({'message':data['Body'], 'mail':chat.ai.me['mail'], 'subject':data['Summary']})
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