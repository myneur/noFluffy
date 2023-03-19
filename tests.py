import yaml
import time

#import sys
#sys.path.append('../')
from chat import AI
#sys.path.remove('../')

def classifier_test():
	tests = yaml.safe_load(open('testdata/classified.tests.yaml', 'r'))
	output = open("testdata/classified.report.yml", "w")

	passed = 0
	failed = 0
	price = 0
	tokens = 0
	report = {'ok': [], 'ko':[]}
	
	classifier = AI()

	for test in tests:
		
		print (test['q'])
		
		
		t = time.time()
		reply = classifier.chat(test['q'], '_classifier')
		t = time.time()-t
		print(t)
		if reply != test['ok']:
			test['ko'] = reply
			tes['seconds'] = round(t, 1)
			report['ko'].append(test)
			print(test)
		else:
			test.pop['ko']
			report['ok'].append(test)

		return # TESTING TEST FIRST!!
	
	yaml.dump(report, output)
    

classifier_test()