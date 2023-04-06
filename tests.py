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
		
	def loadCases(self, file):
		try:
			with open(file, 'r') as file:
				self.cases = yaml.safe_load(file)
				return self.cases
		except Exception as e:
			print(e)
		try:
			print("Starting testing of {} cases".format(len(self.cases)))
		except:
			print("No cases to test")
			return


	def getPrice(self, usage):
		price = (0.002/usage['prompt_tokens'] + 0.002/usage['prompt_tokens'])/100 # TODO variants for GPT4
		self.totalPrice += price
		return round(price, 4)


	def run_sub_test_pattern(self, cases, assertion):
		pass
		for case in test_cases:
			with self.subTest(case=case):
				pass
				try:
					assertion(case)
				except AssertionError:
					failed_subcases += 1
				pass
		print(f"Failed subcases: {failed_subcases}")


	def run_sub_test_template(self, mode, cases, assertion):

		self.mode = mode
		self.ai = AI(self.mode)

		cases = self.loadCases(cases)

		for case in cases:

			t = time.time()
			response = self.ai.chat(case['q'])
			t = time.time()-t
			
			result = response['choices'][0]['message']['content']
			
			price = self.getPrice(response['usage'])
			casePreview = case['q'][:40]+'…'
			
			self.prompts += 1
			self.totalTime += t

			with self.subTest(case=case):

				t = round(t, 1)
				
				try:
					assertion(result, case, t, price, casePreview)
					if 'ko' in case:
						del case['ko']
					case['price'] = price
					self.report['ok'].append(case.copy())
					self.passed += 1
					print(f"""✅ {result}: "{casePreview}" """)
				except AssertionError:
					case['ko'] = result
					case['seconds'] = t
					case['price'] = price
					self.report['ko'].append(case.copy())
					self.failed += 1
					#raise
					print(f"""❌ '{result}' != '{case['ok']}': "{casePreview}" """)

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



class TestClassifier(TestFramework):

	def test_classifier_classification(self):
		def assertion(result, case, t, price, casePreview):
			self.assertEqual(result, case['ok'], f'${price}/{t}s: {casePreview}')
			# OR self.assertIn(case[required_attribute], result)   
		self.run_sub_test_template("_classifier", "testdata/classified.yaml", assertion)



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