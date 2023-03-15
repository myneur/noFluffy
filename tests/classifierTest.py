from chat import AI

data = [
["general-asistance", "So what is the latest version of an Android system that you know about"],
["general-asistance","Show me an example of an inheritance in Python."],

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