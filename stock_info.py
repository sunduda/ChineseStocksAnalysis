import json
import requests
import re
import json
import pandas as pd
from bs4 import BeautifulSoup

class ChinaStockInfo():
    def __init__(self):
        self._params = {
                # Financial form type, mandatory
                'type': 'CWBB_REPORTTYPE',
                # Access token, mandatory
                'token': '70f12f2f4f091e459a279469fe49eca5',
                # Notice date
                'st': 'noticedate',
                # Unknown, keep it -1
                'sr': -1,
                # Current page
                'p': 1,
                # Number of items listed in one page
                'ps': 50,
                # Requesting JavaScript, mandatory
                'js': 'var EsLwgpdo={pages:(tp),data: (x),font:(font)}',
                # Filter condition
                'filter': '(reportdate=^REPORTYEAR-12-31^)',
                # Unknown, optional
                #'rt': 51294261
        }
        self._url = 'http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?'


    def get_table(self, report_type, start_year, end_year):
        df = pd.DataFrame()
        rt_dict = {0:'ZCFZB20', 1:'LRB20', 2:'XJLLB20'}
        params = self._params.copy()
        params['type'] = re.sub('REPORTTYPE', 
                                rt_dict[report_type], 
                                params['type'])
        paramsy = params.copy()
        for y in range(start_year, end_year + 1):
            paramsy['filter'] = re.sub(  'REPORTYEAR', 
                                        str(y), 
                                        params['filter'])
            response = requests.get(self._url, params=paramsy).text
            page_all = int(re.search(re.compile(
                                                r'var.*?{pages:(\d+),data:.*?'),
                                                response).group(1))
            for pg in range(1, page_all + 1):
                params['p'] = pg
                if pg > 1:
                    response = requests.get(self._url, params=paramsy).text
                df = df.append(self.extract_data(response))

        """start_coli = df.columns.get_loc('eutime') + 1
        df.iloc[:, start_coli:] = df.iloc[:, start_coli:]\
                                    .apply( pd.to_numeric, 
                                            axis = 0, 
                                            args = ('ignore', 'float'))"""
        df = df.set_index(['scode', 'reportdate'], drop = True)
        
        xls_writer = pd.ExcelWriter('FinancialReports.xlsx')
        df.to_excel(xls_writer, 'BalanceSheet')
        xls_writer.save()
        print('Finished!')

    def extract_data(self, response):
        items = json.loads(re.search(   re.compile('var.*?data: (.*),font', re.S), 
                                        response).group(1))
        font_mapping = json.loads(re.search(re.compile('var.*?"FontMapping":(.*)}}', re.S),
                                            response).group(1))
        digit_mapping = {}
        for d in font_mapping:
            digit_mapping[d['code']] = str(d['value'])
        """for v in digit_mapping.keys():
            for d in items:
                for k in d.keys():
                    d[k] = re.sub(digit_mapping[v], v, d[k])
        df = df.append(pd.DataFrame(items,columns = items[0].keys()))"""
        return pd.DataFrame(items, columns = items[0].keys())\
                 .replace( digit_mapping, regex = True )

csi = ChinaStockInfo()
csi.get_table(0, 2015, 2017)