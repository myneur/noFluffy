import unittest
import yaml
import time

#import sys
#sys.path.append('../')
from chat import AI
#sys.path.remove('../')

import integrations

convert = integrations.Convertor()


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

		self.field = 'Equals'
		
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

		for case in cases:

			t = time.time()
			response = self.ai.chat(case['q'])
			t = time.time()-t
			
			result = response['choices'][0]['message']['content']
			
			price = self.getPrice(response['usage'])
			casePreview = case['q'][:80].replace(r"\n", " ")+'…'
			
			self.prompts += 1
			self.totalTime += t

			with self.subTest(case=case):

				t = round(t, 1)
				
				try:
					assertion(result, case) #assertion(result, case, t, price, casePreview)
					if 'ko' in case:
						del case['ko']
					case['price'] = price
					self.report['ok'].append(case.copy())
					self.passed += 1
					print(f"""✅ "{casePreview}" """)
				except AssertionError:
					case['ko'] = result
					case['seconds'] = t
					case['price'] = price
					self.report['ko'].append(case.copy())
					self.failed += 1
					if self.field == 'Equals':
						resultPreview = result
					else:
						resultPreview = self.field +": "+ convert.yaml2json(result)[self.field]
					resultPreview = resultPreview.replace(r"\n", " ")
					#raise
					print(f"""❌ '{resultPreview}' INSTEAD '{case[self.field]}': "{casePreview}" """)
				except Exception as e:
					print("Error:", e)

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
		def assertion(result, case):
			#self.assertEqual(result, case['ok'], f'${price}/{t}s: {casePreview}')
			self.assertEqual(result, case['Equals'])
			# OR self.assertIn(result, case['Keys'])   

		cases = self.loadCases("testdata/classifier.yaml")
		#cases = [case for case in cases if 'ko' in case]
		#cases = cases[:1]
		self.run_sub_test_template("_classifier", cases, assertion)

	def test_yaml_classifier_classification(self):
		def assertion(result, case):
			result = convert.yaml2json(result)
			#self.assertIn('service', case.keys())
			for f in ('service', 'command', 'content_type'):
				self.field = f
				self.assertEqual(result[f].lower(), case[f].lower())

		cases = self.loadCases("testdata/classifier.yaml")
		self.run_sub_test_template("_classifier3", cases, assertion)



"""if __name__ == '__main__':
	unittest.main()"""


if __name__ == '__main__':
	unittest.main()
	"""suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestClassifier)
	result = unittest.TestResult()
	suite.run(result)
	print("Tests Run: ", result.testsRun)
	print("Tests Failed: ", len(result.failures))
	print("Tests Passed: ", result.testsRun - len(result.failures))"""