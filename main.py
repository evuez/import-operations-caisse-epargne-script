#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
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
			'MM$TELECHARGE_OPERATIONS$m_ExDDLListeComptes': 'C#{0}#{1}#EUR'.format(self.client_iban, self.today.strftime('%Y%m%d')),
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

		self._authenticate()
		self._load(start, end)
		return self._retrieve()

bank = Bank(CLIENT_ID, CLIENT_SECRET, CLIENT_IBAN)
print bank.get_transactions()