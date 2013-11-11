#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from settings import CLIENT_ID, CLIENT_SECRET, CLIENT_IBAN

class Bank(object):
	AUTH_URL = 'https://www.net444.caisse-epargne.fr/login.aspx'
	LOAD_URL = 'https://www.net444.caisse-epargne.fr/Portail.aspx'
	RTRV_URL = 'https://www.net444.caisse-epargne.fr/Pages/telechargement.aspx'

	MAX_DAYS_AGO = 60
	MIN_DAYS_AGO = 1
	def __init__(self, client_id, client_secret, client_iban):
		self.client_id = client_id
		self.client_secret = client_secret
		self.client_iban = client_iban

		self.today = date.today()

		self.request = requests.session()

		self._authenticate()
	def _authenticate(self):
		auth_payload = {
			'codconf': CLIENT_SECRET,
			'nuabbd': CLIENT_ID,
			'ctx': '',
			'ctx_routage': ''
		}
		self.request.post(
			self.AUTH_URL,
			verify=True,
			data=auth_payload
		)
	def _load(self, start, end):
		load_payload = {
			'MM$TELECHARGE_OPERATIONS$ddlChoixLogiciel': '2', # 2 qif, 3 csv
			'MM$TELECHARGE_OPERATIONS$groupeDate': 'fourchette',
			'MM$TELECHARGE_OPERATIONS$m_DateDebut$txtDate': start,
			'MM$TELECHARGE_OPERATIONS$m_DateFin$txtDate': end,
			'MM$TELECHARGE_OPERATIONS$m_ExDDLListeComptes': 'C#{0}#{1}#EUR'.format(self.client_iban, (date.today() - timedelta(days=3)).strftime('%Y%m%d')),
			'__ASYNCPOST': 'true',
			'__EVENTARGUMENT': '',
			'__EVENTTARGET': 'MM$TELECHARGE_OPERATIONS$m_ChoiceBar$lnkRight',
			'__EVENTVALIDATION': '***REMOVED***',
			'__LASTFOCUS': '',
			'__VIEWSTATE': '***REMOVED***',
			'm_ScriptManager' :'MM$m_UpdatePanel|MM$TELECHARGE_OPERATIONS$m_ChoiceBar$lnkRight'
		}
		load_headers = {
			'Host': 'www.net444.caisse-epargne.fr',
			'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0 Iceweasel/20.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate',
			'X-MicrosoftAjax': 'Delta=true',
			'Cache-Control': 'no-cache',
			'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
			'Referer': 'https://www.net444.caisse-epargne.fr/Portail.aspx',
			'Connection': 'keep-alive',
			'Pragma': 'no-cache'
		}
		self.request.post(
			self.LOAD_URL,
			verify=True,
			data=load_payload,
			headers=load_headers
		)
	def _retrieve(self):
		return self.request.get(self.RTRV_URL, verify=True).text.encode('utf8')
	def get_transactions(self, from_days_ago=MAX_DAYS_AGO, to_days_ago=MIN_DAYS_AGO):
		if from_days_ago < to_days_ago:
			raise Exception("Starting date must be inferior to ending date")
		if to_days_ago < self.MIN_DAYS_AGO:
			raise Exception("Ending date cannot be superior to {0} day(s) ago".format(self.MIN_DAYS_AGO))
		if from_days_ago > self.MAX_DAYS_AGO:
			raise Exception("Cannot retrieve transactions prior to {0} day(s)".format(self.MAX_DAYS_AGO))
		start = (self.today - timedelta(days=from_days_ago)).strftime('%d/%m/%Y')
		end = (self.today - timedelta(days=to_days_ago)).strftime('%d/%m/%Y')

		self._load(start, end)
		return self._retrieve()
	def get_balance(self):
		soup = BeautifulSoup(self.request.get(self.LOAD_URL, verify=True).text.encode('utf8'))
		balance = soup \
			.find(id='MM_SYNTHESE') \
			.find(class_='panel') \
			.find(class_='accompte') \
			.find(class_='rowHover') \
			.find(class_='somme')
		return balance.get_text().encode('utf8')


class ArgumentRequired(Exception):
	pass

class TransactionRequired(Exception):
	pass

class NoTransactionsLoaded(Exception):
	pass

class Transaction(object):
	def __init__(self):
		self.date = None
		self.amount = None
		self.memo = None
		self.cleared = None
		self.number = None
		self.payee = None
		self.address = None
		self.category = None
		self.flag = None
		self.split_category = None
		self.split_memo = None
		self.split_amount = None

class Transactions(object):
	"""
	Holds a list Transaction objects
	Can load new Transaction object from
	a QIF file or string
	"""
	FILE_START = '!Type:'
	ENTRY_START = '^'
	FIELDS = {
		'D': 'date',
		'T': 'amount',
		'M': 'memo',
		'C': 'cleared',
		'N': 'number',
		'P': 'payee',
		'A': 'address',
		'L': 'category',
		'F': 'flag',
		'S': 'split_category',
		'E': 'split_memo',
		'$': 'split_amount'
	}
	def __init__(self, file_=None, str_=None):
		self.cursor = 0
		self.qif = None
		self.transactions = []
		try:
			self.load_qif(file_, str_)
		except ArgumentRequired:
			pass
	def __add__(self, transaction):
		if not isinstance(transaction, Transaction):
			raise TransactionRequired
		self.transactions.append(transaction)
		return self
	def __getitem__(self, key):
		return self.transactions[key]
	def __iter__(self):
		return self
	def next(self):
		try:
			self.cursor += 1
			return self[self.cursor - 1]
		except IndexError:
			raise StopIteration
	def first(self):
		try:
			return self[0]
		except IndexError:
			return None
	def last(self):
		try:
			return self[-1]
		except IndexError:
			return None
	def current(self):
		try:
			return self[self.cursor]
		except IndexError:
			raise None
	def load_file(self, file_):
		with open(file_, 'r') as transactions:
			str_ = transactions.read()
		return self.load_str(str_)
	def load_str(self, str_):
		self.qif = str_
		return str_.splitlines()[::-1]
	def write(self, file_):
		if self.qif is None:
			raise NoTransactionsLoaded
		with open(file_, 'w') as f:
			f.write(self.qif)
	def parse_qif(self, qif_lines):
		for l in qif_lines:
			if l.startswith(self.FILE_START):
				break
			if l == self.ENTRY_START:
				self += Transaction()
			if l[0] in self.FIELDS:
				setattr(
					self[-1],
					self.FIELDS[l[0]],
					l[1:]
				)
		return self
	def load_qif(self, qif_file=None, qif_str=None):
		self.transactions = [] # reset transactions when loading new file or string
		if any((qif_file, qif_str)) is False:
			raise ArgumentRequired
		if qif_file is not None:
			lines = self.load_file(qif_file)
		elif qif_str is not None:
			lines = self.load_str(qif_str)
		return self.parse_qif(lines)