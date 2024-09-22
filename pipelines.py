from ai import AI
import integrations

import yaml
import re

import traceback

class Pipelines:
	def __init__(self, chat):
		self.convert = integrations.Convertor()
		self.services = integrations.Services()
		self.classifier = None
		self.chat = chat

	def execute(self, text, mode=None):
		chat = self.chat
		if not mode:
			mode = AI.modes[chat.ai.mode]
		pipeline = mode['pipeline'] if 'pipeline' in mode else None
		print('…thinking\n')
		if pipeline:
			print(1)
			for step in pipeline:
				print(2)
				if step in chat.ai.modes.keys():
					text = chat.ask(text, AI(step))
				elif step == 'self':
					print(3)
					text = chat.ask(text)
					print(4)
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
		""" executes a method in this class indicated by _classifier """

		print("…classifying ")
		if not self.classifier:
			self.classifier = AI('_classifier')
		action = self.chat.ask(self.convert.first_sentences(question), self.classifier)  # TODO do it singleton 
		
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
			self.chat.ai.memory.data['languages']  = [json['from'], json['to']]
		except: 
			print("Error: did not classify the languages.")
		return output


	def read_message(self, text):
		#filters = self.chat.ask(text, AI('_text_to_imap'))
		filters = self.chat.ask(text, AI('_read_message'))
		filters = self.convert.yaml2json(filters)
		filters = self.convert.remove_empty(filters)
		try:
			filters.pop('service') # TODO ignoring other services so far, everything is mail for now
			filters.pop('filters') # TODO needs more handling to be done
		except:
			pass

		message = self.services.read_mail(filters)
		body = message['content']

		if len(body)> 4000:
			print("…summarizing long mail")
			limit = 2000
			if self.chat.ai.count_tokens(body) > limit: # TODO move to AI
				body = self.chat.ai.cut_to_tokens(body, limit)

			reply = self.chat.ask(body, AI('summarize_message'))
			if reply:
				body = "Summarization of mail:\n"+reply

		body = self.convert.links_to_preview(body)
		body = self.convert.remove_long_literals(body)
		
		self.chat.ai.add_message(text, 'user')
		self.chat.ai.add_message(body)

		try:
			text = f"{message['From']}: {message['Subject']}\n{body}"
		except:
			text = body

		return text


	def send_recent(self, question): 
		print('…preparing message')
		chat = self.chat
		response = chat.ask(question, AI('_send_message'))
		if response:
			try:
				data = self.convert.yaml2json(response)
				if 'message' not in data:
					data['message'] = response
			
			except Exception as e:
				print (e) 
				data = {'message':response, 'subject': 'note to myself'}

			try:
				if data['message'] in ('this-conversation', 'last-message'):
					data['message'] = chat.ai.get_last_reply()['message']

				try:
					summary = chat.ask(data['message'], AI('_summarize_to_subject'))
					data['summary'] = summary if summary else "Our last conversation"
					response = "Sending message to: {}.\nBy: {}.\nSubject: {}.".format(data['recipients'], data['service'], data['summary'])

					#self.services.mailLast({'message': data['message'], 'mail': data['recipients'], 'subject': data['summary']})
					sender = self.chat.ai.memory.data['assistant']['mail']

					to = self.chat.ai.memory.data['me']['mail']
					# TODO DEMO ! sending only to myself so far!

					self.services.send_mail(sender, to, data['summary'], data['message'])
				except Exception as e:
					print(f"Error: {type(e).__name__}: {e}, {e.args} ")
					traceback.print_exc()
					#print(data)

			except Exception as e:
				print("Error in creating the message. Needs review:(")
				print(f"Error: {type(e).__name__}: {e}")
			return response

	def improve_prompt(self, question=""):
		explainer = AI("_improve")
		explainer.messages += self.chat.messages
		
		if not question:
			print("What was the expected output?")
			question = input()

		explainer.messages[1]['content'] = "SYSTEM MESSAGE:\n"+explainer.messages[1]['content']
		explainer.messages[-2]['content'] = "PROMPT:\n"+explainer.messages[-2]['content']
		explainer.messages[-1]['content'] = "CHAT GPT REACTION:\n"+explainer.messages[-1]['content']
		
		question = "EXPECTED REACTION:\n"+ question
		print("…debugging")
		reply = explainer.chat(question)
		self.chat.reply(reply['choices'][0]['message']['content']) # TODO handle errors
		return reply

	def inbox(self, question):
		print('…summarizing inbox')
		time.sleep(3)
		return self.services.summarize_mailbox()

	def calendar(self, question):
		print('…summarizing inbox')
		return self.services.schedule_meeting(question)


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