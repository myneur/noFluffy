def populateTestMailbox(self):
	#mails = yaml.safe_load(open('logs/in.yaml', 'r'))
	to = "Petr Meissner <example@mail.com>"
	dummyMail = self.data['me']['mail']
	mails = [{'Contact': "Mark", 'Subject':"Design Approval Request"}]
	if( input() == 'yes'):
		for mail in mails:
			from_address = mail['Contact'] + dummyMail
			print("{}: {}".format(mail['Contact'], mail['Subject']))
			self.mail(from_address, to, mail['Subject'], mail['Subject'])