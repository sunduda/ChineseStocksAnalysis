import json
import requests
import re
import json
import pandas as pd
import numpy as np

class ChinaCompanyInfo():
    def __init__(self):
        self._t_params = {
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
        self._rt_dict = {0:'ZCFZB20', 1:'LRB20', 2:'XJLLB20'}
        self.sheet_titles = ('BalanceSheet', 'IncomeStatement', 'CashFlowStatement')
        self.df_fr = [pd.DataFrame(), pd.DataFrame(), pd.DataFrame()]
        self._ind_dict = {}

    def get_table(self, report_type, start_year, end_year):
        t_params = self._t_params.copy()
        # Determine financial report type
        t_params['type'] = re.sub('REPORTTYPE', self._rt_dict[report_type], self._t_params['type'])
        params = t_params.copy()

        # Go through all the annual reports within the duration
        for y in range(start_year, end_year + 1):
            # Determine the year of this annual report
            params['filter'] = re.sub('REPORTYEAR', str(y), t_params['filter'])
            # Request a response from the data url
            response = requests.get(self._url, params=params).text
            # Get the number of all pages containing the information
            page_all = int(re.search(re.compile(r'var.*?{pages:(\d+),data:.*?'),response).group(1))
            
            # Go through all the pages to get all the stock information this
            # url has to offer
            for pg in range(1, page_all + 1):
                params['p'] = pg
                if pg > 1:
                    response = requests.get(self._url, params=params).text
                self.df_fr[report_type] = self.df_fr[report_type].append(self.extract_data(response))

        for i in range(len(self.df_fr[report_type].columns)):
            # Convert all numeric strings to integer or float
            self.df_fr[report_type].iloc[:, i] = self.df_fr[report_type].iloc[:, i].apply(pd.to_numeric, errors='ignore')
            # Remove time strings from dataframe
            if self.df_fr[report_type].iloc[:, i].apply(type).eq(str).all():
                self.df_fr[report_type].iloc[:, i] = self.df_fr[report_type].iloc[:, i].str.replace(r'T\d\d:\d\d:\d\d', '', case = True)
        
        # Set the indices to columns with unique and non-null values
        self.df_fr[report_type]['reportdate'] = pd.to_datetime(self.df_fr[report_type]['reportdate'], format = '%Y/%m/%d').dt.date
        self.df_fr[report_type]['noticedate'] = pd.to_datetime(self.df_fr[report_type]['noticedate'], format = '%Y/%m/%d').dt.date
        self.df_fr[report_type]['eutime'] = pd.to_datetime(self.df_fr[report_type]['eutime'], format = '%Y/%m/%d').dt.date
        self.df_fr[report_type] = self.df_fr[report_type].set_index(['scode', 'reportdate'], drop = True)

        # Save this dataframe
        self.save_dataframe(report_type)
        
        print('Finished!')
    
    def stock_ind(self):
        self._ind_dict = {}
        for i in range(3):
            if 'publishname' not in list(self.df_fr[i].columns):
                continue
            for index, line in self.df_fr[i].iterrows():
                field = line['publishname']
                if (index[0] not in self._ind_dict.keys()) and (not pd.isnull(field)):
                    self._ind_dict[index[0]] = field

    def extract_data(self, response):
        items = json.loads(re.search(re.compile('var.*?data: (.*),font', re.S), response).group(1))
        font_mapping = json.loads(re.search(re.compile('var.*?"FontMapping":(.*)}}', re.S), response).group(1))
        digit_mapping = {}
        for d in font_mapping:
            digit_mapping[d['code']] = str(d['value'])
        df = pd.DataFrame(items, columns = items[0].keys()).replace(digit_mapping, regex = True)
        df = df.replace('^-$', 0, regex = True)
        return df

    def save_dataframe(self, st):
        
        self.df_fr[st].to_pickle(self.sheet_titles[st] + '.pkl')
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        xlsx_writer = pd.ExcelWriter(   self.sheet_titles[st] + '.xlsx', 
                                        engine='xlsxwriter', 
                                        datetime_format='yyyy/mm/dd', 
                                        date_format='yyyy/mm/dd')
        # Convert the dataframe to an XlsxWriter Excel object.
        df = self.df_fr[st].copy().reset_index()
        df.to_excel(xlsx_writer, sheet_name=self.sheet_titles[st], index = False)
        df_cols = tuple(df.columns)

        # Get the xlsxwriter workbook and worksheet objects.
        workbook = xlsx_writer.book
        worksheet = xlsx_writer.sheets[self.sheet_titles[st]]

        special_cols = [   [-1, '00000#', 'scode'], 
                            [-1, '0000#', 'hycode'], 
                            [-1, '0000000#', 'companycode'], 
                            [-1, '0#.000000000', 'tsatz'], 
                            [-1, '0#.000000000', 'tdetz'], 
                            [-1, '0#.000000000', 'ld'], 
                            [-1, '0#.000000000', 'zcfzl'], 
                            [-1, '0#.000000000', 'tystz'], 
                            [-1, '0#.000000000', 'yltz'], 
                            [-1, '0#.000000000', 'sjltz'], 
                            [-1, '0#.000000000', 'sjlktz']]
        for sc in special_cols:
            try:
                sc[0] = df_cols.index(sc[2])
            except ValueError:
                sc[0] = -1
                            
        # Set the column width and format.
        for sc in special_cols:
            if sc[0] != -1:
                cformat = workbook.add_format({'num_format': sc[1], })
                worksheet.set_column(sc[0], sc[0], None, cformat)
        for ci in range(df_cols.index('eutime')+1, len(df_cols)):
            if ('_tb' in df_cols[ci]) or ('_zb' in df_cols[ci]):
                cformat = workbook.add_format({'num_format': '0#.000000000', })
                worksheet.set_column(ci, ci, None, cformat)
            elif (df_cols[ci] not in [s[0] for s in special_cols]):
                cformat = workbook.add_format({'num_format': '0#.00', })
                worksheet.set_column(ci, ci, None, cformat)
        
        # Note: It isn't possible to format any cells that already have a format such
        # as the index or headers or any cells that contain dates or datetimes.
        
        xlsx_writer.save()
    
    def load_dataframe(self, st):
        self.df_fr[st] = pd.read_pickle(self.sheet_titles[st] + '.pkl')

    def clean_dataframe(self):
        for i in range(3):
            if 'publishname' not in list(self.df_fr[i].columns):
                continue
            keys = list(x for x in self.df_fr[i][pd.isnull(self.df_fr[i]['publishname'])].index.get_level_values(0))
            
            try:
                self.df_fr[i].loc[keys, 'publishname'] = self._ind_dict[tuple(keys)]
            except KeyError:
                self.df_fr[i] = self.df_fr[i].drop(keys, axis = 0, level = 0)
            self.df_fr[i] = self.df_fr[i].drop(['hycode', 
                                                'companycode', 
                                                'sname', 
                                                'mkt', 
                                                'reporttimetypecode', 
                                                'combinetypecode', 
                                                'dataajusttype', 
                                                'noticedate', 
                                                'eutime'], axis = 1)

    def industry_to_number(self, rt):
        ind_set = sorted(list(set(self._ind_dict.values())))
        di = dict(zip(ind_set, range(len(ind_set))))
        if 'publishname' not in list(self.df_fr[rt].columns):
            raise ValueError('The' + self.sheet_titles[rt] + 'dataframe is empty!')
        self.df_fr[rt] = self.df_fr[rt].replace({"publishname": di})

    def number_to_industry(self, rt):
        ind_set = sorted(list(set(self._ind_dict.values())))
        di = dict(zip(range(len(ind_set)), ind_set))
        if 'publishname' not in list(self.df_fr[rt].columns):
            raise ValueError('The' + self.sheet_titles[rt] + 'dataframe is empty!')
        self.df_fr[rt] = self.df_fr[rt].replace({"publishname": di})