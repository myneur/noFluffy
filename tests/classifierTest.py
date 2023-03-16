from chat import AI

data = [
["none", """Show me how that prompt would look like for you, GPT-3. In the example, use categories of actions communications, todo, maps and web search."""]

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