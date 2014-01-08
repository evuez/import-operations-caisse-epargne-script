#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
from bs4 import BeautifulSoup
from datetime import date, timedelta
from settings import CLIENT_ID, CLIENT_SECRET, CLIENT_IBAN, BANK_CODE, BANK_DATE

class Bank(object):
	BASE_URL = 'www.net{bank_code}.caisse-epargne.fr'.format(bank_code=BANK_CODE)
	AUTH_URL = 'https://{0}/login.aspx'.format(BASE_URL)
	LOAD_URL = 'https://{0}/Portail.aspx'.format(BASE_URL)
	RTRV_URL = 'https://{0}/Pages/telechargement.aspx'.format(BASE_URL)

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
		headers = {
			'Host': self.BASE_URL,
			'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0 Iceweasel/20.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate',
			'X-MicrosoftAjax': 'Delta=true',
			'Cache-Control': 'no-cache',
			'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
			'Referer': self.LOAD_URL,
			'Connection': 'keep-alive',
			'Pragma': 'no-cache'
		}
		soup = BeautifulSoup(self.request.get(self.LOAD_URL, verify=True).text.encode('utf8'))
		preload_payload = {
			'__ASYNCPOST': 'true',
			'__EVENTARGUMENT': 'CPTDMTE0',
			'__EVENTTARGET': 'MM$m_PostBack',
			'__EVENTVALIDATION': soup.find(id='__EVENTVALIDATION')['value'],
			'__LASTFOCUS': '',
			'__VIEWSTATE': soup.find(id='__VIEWSTATE')['value'],
			'm_ScriptManager' :'MM$m_UpdatePanel|MM$m_PostBack'
		}

		html = self.request.post(
			self.LOAD_URL,
			verify=True,
			data=preload_payload,
			headers=headers
		).text.encode('utf8')

		soup = BeautifulSoup(html)
		accounts = soup.find(id='MM_TELECHARGE_OPERATIONS_m_ExDDLListeComptes').findAll('option')
		account = [a for a in accounts if CLIENT_IBAN in a['value']][0]['value']

		load_payload = {
			'MM$TELECHARGE_OPERATIONS$ddlChoixLogiciel': '2', # 2 qif, 3 csv
			'MM$TELECHARGE_OPERATIONS$groupeDate': 'fourchette',
			'MM$TELECHARGE_OPERATIONS$m_DateDebut$txtDate': start,
			'MM$TELECHARGE_OPERATIONS$m_DateFin$txtDate': end,
			'MM$TELECHARGE_OPERATIONS$m_ExDDLListeComptes': account,
			'__ASYNCPOST': 'true',
			'__EVENTARGUMENT': '',
			'__EVENTTARGET': 'MM$TELECHARGE_OPERATIONS$m_ChoiceBar$lnkRight',
			'__EVENTVALIDATION': re.search(r'\|hiddenField\|__EVENTVALIDATION\|(.*)\|12\|asyncPostBackControlIDs\|', html).group(1),
			'__LASTFOCUS': '',
			'__VIEWSTATE': '',
			'm_ScriptManager' :'MM$m_UpdatePanel|MM$TELECHARGE_OPERATIONS$m_ChoiceBar$lnkRight'
		}

		self.request.post(
			self.LOAD_URL,
			verify=True,
			data=load_payload,
			headers=headers
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
		return balance.get_text().replace(u'\u00A0', ' ').encode('utf8')

class ArgumentRequired(Exception):
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
	def __eq__(self, other):
		return self.__dict__ == other.__dict__
	def __ne__(self, other):
		return self.__dict__ != other.__dict__
	def __str__(self):
		return str(self.__dict__)
	def __hash__(self):
		return hash(str(self))

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
		self.transactions = []
		try:
			self.load_qif(file_, str_)
		except ArgumentRequired:
			pass
	def __add__(self, other):
		if not isinstance(other, Transaction):
			raise NotImplementedError
		self.transactions.append(other)
		return self
	def __getitem__(self, key):
		return self.transactions[key]
	def __iter__(self):
		return self
	def extend(self, other):
		if not isinstance(other, set):
			raise NotImplementedError
		self.transactions.extend(other)
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
	def reset(self):
		self.cursor = 0
	def load_file(self, file_):
		with open(file_, 'r') as transactions:
			str_ = transactions.read()
		return self.load_str(str_)
	def load_str(self, str_):
		return str_.splitlines()[::-1]
	def update(self, transactions):
		self.extend(set(transactions) - set(self.transactions))
		return self
	def write(self, file_):
		if not self.transactions:
			raise NoTransactionsLoaded
		r_fields = {v:k for k,v in self.FIELDS.iteritems()}
		contents = '{0}Bank\n'.format(self.FILE_START)
		for x in self[::-1]:
			for k,v in x.__dict__.iteritems():
				if v is not None:
					contents += '{0}{1}\n'.format(r_fields[k], v)
			contents += '{0}\n'.format(self.ENTRY_START)
		with open(file_, 'wb') as f:
			f.write(contents)
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
	def load_qif(self, file_=None, str_=None):
		self.transactions = [] # reset transactions when loading new file or string
		if any((file_, str_)) is False:
			raise ArgumentRequired
		if file_ is not None:
			lines = self.load_file(file_)
		elif str_ is not None:
			lines = self.load_str(str_)
		return self.parse_qif(lines)