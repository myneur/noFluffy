import unittest
import yaml
import time

#import sys
#sys.path.append('../')
from chat import AI
#sys.path.remove('../')


class TestFramework(unittest.TestCase):
	# todo generalizling
	def setUp(self):
		self.cases = None
		self.ai = None
		self.mode = None
		self.delay = 1

		self.passed = 0
		self.failed = 0
		
		self.prompts = 0

		self.totalPrice = 0
		self.totalTime = 0
		
		self.report = {'ok': [], 'ko':[]}
		
	def loadCases(file):
		try:
			with open(file, 'r') as file:
				self.cases = yaml.safe_load(file)
		except Exception as e:
			print(e)

	def getPrice(usage):
		price = (0.002/usage['prompt_tokens'] + 0.002/usage['prompt_tokens'])/100 # TODO variants for GPT4
		self.totalPrice += price
		return round(price, 4)

	def test_template(self):	
		self.ai = AI(self.mode)

		loadCases('testdata/classified.cases.yaml')
		try:
			print("Starting testing of {} cases".format(len(self.cases)))
		except:
			print("No cases to test")
			return


		for case in self.cases:	
			t = time.time()

			response = self.ai.chat(case['q'])

			t = time.time()-t
			
			result = response['choices'][0]['message']['content']
			
			price = self.getPrice(response['usage'])
			start = case['q'][:40]+'…'
			
			self.prompts += 1

			t = round(t, 1)
			self.totalTime += t

			with self.subTest(item=case):
				
				try:
					self.assertEqual(result, case['ok'], f'${price}/{t}s: {start}')
					
					self.totalTime += t
					if 'ko' in case:
						del case['ko']
					case['price'] = price
					self.report['ok'].append(case.copy())
					self.passed += 1
					print(f"""✅ {result}: "{start}" """)
				except AssertionError:
					case['ko'] = result
					case['seconds'] = t
					case['price'] = price
					self.report['ko'].append(case.copy())
					self.failed += 1
					#raise
					print(f"""❌ '{result}' != '{case['ok']}': "{start}" """)

			time.sleep(self.delay)


		promptTime = round(self.totalTime, 1)
		print(f"""
Failed cases: {self.failed}
Passed cases: {self.passed}
Prompts cases: {self.prompts}
Total response time: {promptTime} s
Total price: ${self.totalPrice}
""")

		self.report['price'] = self.totalPrice
		with open("testdata/classified.report.yaml", "w") as file:
			yaml.dump(self.report, file)




class TestTranslate(unittest.TestCase):

	def setUp(self):
		self.cases = None
		self.ai = None
		self.delay = 1

		self.passed = 0
		self.failed = 0
		
		self.prompts = 0

		self.totalPrice = 0
		self.totalTime = 0
		
		self.report = {'ok': [], 'ko':[]}
		
	def loadCases(file):
		try:
			with open(file, 'r') as file:
				self.cases = yaml.safe_load(file)
		except Exception as e:
			print(e)

	def test_classifier_assertions(self):	
		loadCases('testdata/classified.cases.yaml')
		try:
			print("Starting testing of {} cases".format(len(self.cases)))
		except:
			print("No cases to test")
			return

		for case in self.cases:	
			t = time.time()

			response = self.classifier.chat(case['q'], '_classifier')

			t = time.time()-t
			

			result = response['choices'][0]['message']['content']
			
			price = (0.002/response['usage']['prompt_tokens'] + 0.002/response['usage']['prompt_tokens'])/100 # TODO variants for GPT4
			self.totalPrice += price

			price = round(price, 4)
			start = case['q'][:40]+'…'
			
			self.prompts += 1

			t = round(t, 1)
			self.totalTime += t

			with self.subTest(item=case):
				
				try:
					self.assertEqual(result, case['ok'], f'${price}/{t}s: {start}')
					self.totalTime += t
					if 'ko' in case:
						del case['ko']
					case['price'] = price
					self.report['ok'].append(case.copy())
					self.passed += 1
					print(f"""✅ {result}: "{start}" """)
				except AssertionError:
					case['ko'] = result
					case['seconds'] = t
					case['price'] = price
					self.report['ko'].append(case.copy())
					self.failed += 1
					#raise
					print(f"""❌ '{result}' != '{case['ok']}': "{start}" """)

			time.sleep(self.delay)


		promptTime = round(self.totalTime, 1)
		print(f"""
Failed cases: {self.failed}
Passed cases: {self.passed}
Prompts cases: {self.prompts}
Total response time: {promptTime} s
Total price: ${self.totalPrice}
""")

		self.report['price'] = self.totalPrice
		with open("testdata/classified.report.yaml", "w") as file:
			yaml.dump(self.report, file)


"""if __name__ == '__main__':
	unittest.main()"""


if __name__ == '__main__':
	unittest.main()
	"""suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTranslate)
	result = unittest.TestResult()
	suite.run(result)
	print("Tests Run: ", result.testsRun)
	print("Tests Failed: ", len(result.failures))
	print("Tests Passed: ", result.testsRun - len(result.failures))"""