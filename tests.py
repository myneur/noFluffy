import unittest
import yaml
import time

#import sys
#sys.path.append('../')
from chat import AI
#sys.path.remove('../')


class TestTranslate(unittest.TestCase):
	def setUp(self):
		with open('testdata/classified.tests.yaml', 'r') as file:
			self.tests = yaml.safe_load(file)
		with open("testdata/classified.report.yaml", "w") as file:
			self.output = file
		self.passed = 0
		self.failed = 0
		self.price = 0
		self.tokens = 0
		self.report = {'ok': [], 'ko':[]}
		self.classifier = AI()

	def test_classifier_assertions(self):
		for test in self.tests:	
			
			t = time.time()
			
			reply = self.classifier.chat(test['q'], '_classifier')
			result = reply['choices'][0]['message']['content']
			
			t = time.time()-t

			
			if self.assertEqual(result, test['ok'], 'in: '+test['q'][:20]+'…'):
				test['ko'] = result
				tes['seconds'] = round(t, 1)
				report['ko'].append(test)
				
			else:
				test.pop['ko']
				report['ok'].append(test)

			return # TESTING TEST FIRST!!
		
		yaml.dump(report, output)


if __name__ == '__main__':
	unittest.main()