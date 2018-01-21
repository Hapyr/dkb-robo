#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" dkb internet banking automation library """

from __future__ import print_function
import sys
import cookielib
from datetime import datetime
import mechanize
from BeautifulSoup import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf8')

class DKBRobo(object):
    """ dkb_robo class """

    base_url = 'https://www.dkb.de'

    def get_account_transactions(self, dkb_br, transaction_url, date_from, date_to):
        """ get transactions from an regular account for a certain amount of time
        args:
            dkb_br          - browser object
            transaction_url - link to collect the transactions
            date_from       - transactions starting form
            date_to         - end date
        """
        dkb_br.open(transaction_url)
        dkb_br.select_form(name="form1615473160_1")

        # fill form
        try:
            one = dkb_br.find_control(name="slBankAccount", nr=0)
            one.value = ['0']
        except:
            pass

        dkb_br["slTransactionStatus"] = ['0']
        dkb_br["searchPeriodRadio"] = ['1']
        dkb_br["slSearchPeriod"] = ['1']
        dkb_br["transactionDate"] = str(date_from)
        dkb_br["toTransactionDate"] = str(date_to)
        tr_response = dkb_br.submit()

        # parse the lines to get transactions from the day
        tr_lines = tr_response.read()

        # enter a loop to check all following pages
        soup = BeautifulSoup(tr_lines)

        # loop into the differnt pages
        loop_cnt = 1

        # we need to set more_pages to true to enter loop
        more_pages = True
        while more_pages:
            # for the moment we assume that there is no further page
            more_pages = False
            loop_cnt += 1
            more_tr = soup.findAll('a', attrs={'class':'gotoPage'})
            for page in more_tr:
                # check if there are more pages to download
                if page.contents[0] == str(loop_cnt):
                    # more pages available fetch/parse the page and enter
                    # while loop again
                    new_link = self.base_url + page['href']
                    mtr_page = dkb_br.open(new_link)
                    mtr_lines = mtr_page.read()
                    tr_lines = tr_lines + mtr_lines
                    more_pages = True
                    break

        transactions_dic = self.parse_account_transactions(tr_lines)

        return transactions_dic

    def get_creditcard_transactions(self, dkb_br, transaction_url, date_from, date_to):
        """ get transactions from an regular account for a certain amount of time
        args:
            dkb_br          - browser object
            transaction_url - link to collect the transactions
            date_from       - transactions starting form
            date_to         - end date
        """

        # get credit card transaction form yesterday
        kk_lines = ''

        more_kktr = None
        dkb_br.open(transaction_url)
        dkb_br.select_form(name="form1579108072_1")
        # br["slAllAccounts"]       = [str(kk)]
        dkb_br["slSearchPeriod"] = ['0']
        dkb_br["filterType"] = ['DATE_RANGE']
        dkb_br["postingDate"] = str(date_from)
        dkb_br["toPostingDate"] = str(date_to)

        kk_response = dkb_br.submit()

        # parse the lines to get transactions from the day
        kk_resp = kk_response.read()
        kk_lines = kk_lines + kk_resp

        # check if there is a another page
        soup = BeautifulSoup(kk_resp)
        more_kktr = soup.findAll('a', attrs={'class':'icons butNext0'})

        while more_kktr:
            # if so get link/transactions from 2nd page
            link = self.base_url + more_kktr[0]['href']
            mkk_page = dkb_br.open(link)
            mkk_lines = mkk_page.read()
            kk_lines = kk_lines + mkk_lines
            soup = BeautifulSoup(mkk_lines)
            more_kktr = soup.findAll('a', attrs={'class':'icons butNext0'})

        transaction_list = self.parse_cc_transactions(kk_lines)

        return transaction_list

    def get_document_links(self, dkb_br, url):
        """ create a dictionary of the documents stored in a pbost folder

        args:
            dkb_br - browser object
            url - folder url

        returns:
            dictionary of the documents
        """
        document_dic = {}

        category_result = dkb_br.open(url)
        soup = BeautifulSoup(category_result.read())
        table = soup.find('table', attrs={'class':'widget widget abaxx-table expandableTable expandableTable-with-sort'})
        if table:
            tbody = table.find('tbody')
            for row in tbody.findAll('tr'):
                link = row.find('a')
                # link_name = link.contents[0]
                # url  = self.base_url + link['href']
                document_dic[link.contents[0]] = self.base_url + link['href']

        return document_dic

    def get_transactions(self, dkb_br, transaction_url, atype, date_from, date_to):
        """ get transactions for a certain amount of time
        args:
            dkb_br          - browser object
            transaction_url - link to collect the transactions
            atype           - account type (cash, creditcard, depot)
            date_from       - transactions starting form
            date_to         - end date

        returns:
            list of transactions; each transaction gets represented as a dictionalry containing the following information
            - date   - booking date
            - amount - amount
            - text   - test
        """
        transaction_list = []
        if atype == 'account':
            transaction_list = self.get_account_transactions(dkb_br, transaction_url, date_from, date_to)
        elif atype == 'creditcard':
            transaction_list = self.get_creditcard_transactions(dkb_br, transaction_url, date_from, date_to)

        return transaction_list

    def login(self, dkb_user, dkb_password):
        """ login into DKB banking area

        args:
            dkb_user = dkb username
            dkb_password  = dkb_password

        returns:
            dkb_br - handle to browser object for further processing
            last_login - last login date (german date format)
            account_dic - dictionary containig account information
            - name
            - account numner
            - type (account, creditcard, depot)
            - account balance
            - date of balance
            - link to details
            - link to transactions
        """
        # login url
        login_url = self.base_url + '/' + 'banking'

        # create browser and login
        dkb_br = self.new_instance()
        dkb_br.open(login_url)

        dkb_br.select_form(name="login")
        dkb_br["j_username"] = str(dkb_user)
        dkb_br["j_password"] = str(dkb_password)

        response = dkb_br.submit()

        # parse the lines to get all account infos
        soup = BeautifulSoup(response.read())

        # filter last login date
        last_login = soup.find("div", attrs={'id':'lastLoginContainer'}).text.strip()
        # remove crlf
        last_login = last_login.replace('\n', '')
        # format string in a way we need it
        last_login = last_login.replace('  ', '')
        last_login = last_login.replace('Letzte Anmeldung:', '')

        # parse account date
        overview_dic = self.parse_overview(soup)

        return(dkb_br, last_login, overview_dic)

    def logout(self, dkb_br):
        """ logout from DKB banking area

        args:
            dkb_br = browser object

        returns:
            None
        """
        logout_url = self.base_url + '/' + 'DkbTransactionBanking/banner.xhtml?$event=logout'
        dkb_br.open(logout_url)

    def new_instance(self):
        """ creates a new browser instance

        args:
           None

        returns:
           dkb_br - instance
        """
        # create browser and cookiestore objects
        dkb_br = mechanize.Browser()
        dkb_cj = cookielib.LWPCookieJar()
        dkb_br.set_cookiejar = dkb_cj

        # configure browser
        dkb_br.set_handle_equiv = True
        dkb_br.set_handle_redirect = True
        dkb_br.set_handle_referer = True
        dkb_br.set_handle_robots = False
        dkb_br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8 GTB7.1 (.NET CLR 3.5.30729)'), ('Accept-Language', 'en-US,en;q=0.5'), ('Connection', 'keep-alive')]

        # initilize some cookies to fool dkb
        dkb_ck = cookielib.Cookie(version=0, name='javascript', value='enabled', port=None, port_specified=False, domain='www.dkb.de', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        dkb_cj.set_cookie(dkb_ck)
        dkb_ck = cookielib.Cookie(version=0, name='BRSINFO_browserPlugins', value='NPSWF32_25_0_0_127.dll%3B', port=None, port_specified=False, domain='www.dkb.de', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        dkb_cj.set_cookie(dkb_ck)
        dkb_ck = cookielib.Cookie(version=0, name='BRSINFO_screen', value='width%3D1600%3Bheight%3D900%3BcolorDepth%3D24', port=None, port_specified=False, domain='www.dkb.de', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        dkb_cj.set_cookie(dkb_ck)

        return dkb_br

    def parse_account_transactions(self, transactions):
        """ parses html code and creates a list of transactions included

        args:
            transactions - html page including transactions

        returns:
            list of transactions captured. Each transaction gets respresented by a hash containing the follwoing values
            - date - booking date
            - amount - amount
            - text - text
        """
        # parse the lines to get all account infos
        soup = BeautifulSoup(transactions)

        # create empty list
        transaction_list = []

        tr_lists = soup.findAll('table', attrs={'id':'umsatzTabelle'})
        for tr_list in tr_lists:
            try:
                rows = tr_list.findAll("tr", attrs={'class':'mainRow'})
            except:
                rows = []

            for row in rows:
                cols = row.findAll("td")
                date = cols[0].find('span', attrs={'class':'valueDate'}).text.strip()
                if date == '':
                    date = 'vorgem.'
                amount = cols[3].text.strip()
                f_amount = amount.replace('.', '')
                f_amount = f_amount.replace(',', '.')

                text = ''
                divs = cols[1].findAll('div')
                if len(divs) > 2:
                    if 'DATUM ' in  str(divs[2].text.strip()):
                        text = divs[0].text.strip() + ' ' + divs[1].text.strip()
                    else:
                        text = divs[0].text.strip() + ' ' + divs[1].text.strip() + divs[2].text.strip()
                else:
                    text = divs[0].text.strip() + ' ' + divs[1].text.strip()

                text = text.replace('  ', ' ')
                text = text.replace('  ', ' ')
                text = text.replace('  ', ' ')
                text = text.replace('  ', ' ')

                # store entry
                tmp_dic = {}
                tmp_dic['amount'] = f_amount
                tmp_dic['date'] = date
                tmp_dic['text'] = text
                transaction_list.append(tmp_dic)

        return transaction_list

    def parse_cc_transactions(self, transactions):
        """ parses html code and creates a list of transactions included

        args:
            transactions - html page including transactions

        returns:
            list of transactions captured. Each transaction gets respresented by a hash containing the follwoing values
            - bdate - booking date
            - vdate - valuta date
            - amount - amount
            - text - text
        """
        # parse the lines to get all account infos
        soup = BeautifulSoup(transactions)

        # create empty dic
        transaction_list = []

        # get kk transactions
        table_lists = soup.findAll("table", attrs={'class':'expandableTable dateHandling '})

        for tr_line in table_lists:

            rows = tr_line.findAll("tr", attrs={'class':'mainRow'})
            for row in rows:
                cols = row.findAll("td")
                vdate = cols[1].find("span", attrs={'class':'valueDate'}).text.strip()
                # reformat date
                vdate = datetime.strptime(vdate, '%d.%m.%y').strftime("%d.%m.%Y")

                try:
                    bdate = cols[1].findAll(text=True)[3].strip()
                    # reformat date
                    bdate = datetime.strptime(bdate, '%d.%m.%y').strftime("%d.%m.%Y")
                except:
                    bdate = vdate

                text = cols[2].text.strip()
                amount = cols[3].find("span").text.strip()
                f_amount = amount.replace('.', '')
                f_amount = f_amount.replace(',', '.')

                tmp_dic = {}
                tmp_dic['bdate'] = bdate
                tmp_dic['show_date'] = bdate
                tmp_dic['vdate'] = vdate
                tmp_dic['store_date'] = vdate
                tmp_dic['text'] = text
                tmp_dic['amount'] = f_amount
                transaction_list.append(tmp_dic)

        return transaction_list

    def parse_overview(self, soup):
        """ creates a dictionary including account information

        args:
            soup - BautifulSoup object

        returns:
            overview_dic - dictionary containg following account information
            - name
            - account numner
            - type (account, creditcard, depot)
            - account balance
            - date of balance
            - link to details
            - link to transactions
        """
        # get account information
        overview_dic = {}
        # to_remove = 0
        counter = 0
        for row in soup.findAll("tr", attrs={'class':'mainRow'}):
            overview_dic[counter] = {}
            cols = row.findAll("td")

            # account name
            overview_dic[counter]['name'] = cols[0].find('div').text.strip()

            # account number
            overview_dic[counter]['account'] = cols[1].text.strip()
            # date
            overview_dic[counter]['date'] = cols[2].text.strip()
            # amount (to be reformated)
            amount = cols[3].text.strip().replace('.', '')
            overview_dic[counter]['amount'] = float(amount.replace(',', '.'))

            # get link for transactions
            link = cols[4].find('a', attrs={'class':'evt-paymentTransaction'})
            if link:
                # thats a cash account or a credit card
                if 'cash' in cols[4].text.strip().lower():
                    # this is a cash account
                    overview_dic[counter]['type'] = 'account'
                else:
                    # this is a credit card
                    overview_dic[counter]['type'] = 'creditcard'
                overview_dic[counter]['transactions'] = self.base_url + link['href']
            else:
                try:
                    # thats a depot
                    overview_dic[counter]['type'] = 'depot'
                    link = cols[4].find('a', attrs={'class':'evt-depot'})
                    overview_dic[counter]['transactions'] = self.base_url + link['href']
                except:
                    pass

            # get link for details
            try:
                link = cols[4].find('a', attrs={'class':'evt-details'})
                overview_dic[counter]['details'] = self.base_url + link['href']
            except:
                pass

            # increase counter
            counter += 1

        return overview_dic

    def scan_postbox(self, dkb_br):
        """ scans the DKB postbox and creates a dictionary out of the
            different documents

        args:
            dkb_br = browser object

        returns:
           dictionary in the following format

           - folder name in postbox
                - details -> link to document overview
                - documents
                    - name of document -> document link
        """
        pb_url = self.base_url + '/banking/postfach'
        pb_result = dkb_br.open(pb_url)
        soup = BeautifulSoup(pb_result.read())
        table = soup.find('table', attrs={'id':'welcomeMboTable'})
        tbody = table.find('tbody')

        pb_dic = {}
        for row in tbody.findAll('tr'):
            link = row.find('a')
            link_name = link.contents[0]
            pb_dic[link_name] = {}
            pb_dic[link_name]['name'] = link_name
            pb_dic[link_name]['details'] = self.base_url + link['href']
            pb_dic[link_name]['documents'] = self.get_document_links(dkb_br, pb_dic[link_name]['details'])

        return pb_dic
