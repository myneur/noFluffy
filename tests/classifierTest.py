from chat import AI

data = [
["none", """Show me how that prompt would look like for you, GPT-3. In the example, use categories of actions communications, todo, maps and web search."""]
"""You already told me that I can use Beware or Kivy to build an application for Android from just 
Python. Show me the code to build next application. It will only select one big button and that button
will run an action called ask and clicking it again just stops that action.""",
"none", """I want to demo my application in a video that will be sent over mail. The application is a purely 
conversational artificial intelligence assistant. The great thing about the assistant is that it 
understands any language well, namely Czech and English. And then, on top of being able to answer 
general questions, it also has functions like an ability to send me an email. What is the best, the 
most jaw-dropping and fun way to present it in the video? Show me a script for such video."""


]


def classifier_test():
	classifier = AI()
	for d in data:
		reply = classifier.chat(d[1], 'classificator')
		if reply != d[0]:
			if d[0] == 'general-asistance' and reply == 'none':
				continue
			print(reply+' instead '+d[1]+': '+d[1])

classifier_test()