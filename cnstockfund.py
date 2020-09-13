# -*- coding: utf-8 -*-
import json
import os
import re

import numpy as np
import pandas as pd
import requests

__version__ = '0.1.0'
__author__ = '杜心达'

__REQ_PARAMS = {
    'type': 'CWBB_REPORTTYPE',  # Financial form type, mandatory
    'token': '70f12f2f4f091e459a279469fe49eca5',  # Access token, mandatory
    'st': 'noticedate',  # Notice date
    'sr': -1,  # Unknown, keep it -1
    'p': 1,  # Current page
    'ps': 50,  # Number of items listed in one page
    'js': 'var EsLwgpdo={pages:(tp),data: (x),font:(font)}',  # JavaScript
    'filter': '(reportdate=^REPORTYEAR-12-31^)',  # Filter condition
    # 'rt': 51294261  # Unknown, optional
}
__REQ_URL = 'http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?'
SHEET_TITLES = ('BalanceSheet', 'IncomeStatement', 'CashFlowStatement')
__RT_DICT = {SHEET_TITLES[0]: 'ZCFZB20',
             SHEET_TITLES[1]: 'LRB20',
             SHEET_TITLES[2]: 'XJLLB20'}


def format_dtypes(data: pd.DataFrame, skip_cols: list = None,
                  inplace: bool = False):
    if skip_cols is None:
        skip_cols = []
    if not inplace:
        data = data.copy()
    for col in data.columns:
        if col in skip_cols:
            continue
        data.loc[:, col] = pd.to_numeric(data.loc[:, col], errors='ignore')
    if not inplace:
        return data


def get_reports(report_type: str, start_year: int, end_year: int, **kwargs):
    save_dir = kwargs.pop('save_dir', None)

    req_params = __REQ_PARAMS.copy()
    req_params.update(kwargs)
    report_data = pd.DataFrame()
    # Go through all the annual reports within the duration
    for y in range(start_year, end_year + 1):
        # Determine financial report type
        # Determine the year of this annual report
        req_params.update({'type': re.sub('REPORTTYPE', __RT_DICT[report_type],
                                          __REQ_PARAMS['type']),
                           'filter': re.sub('REPORTYEAR', str(y),
                                            __REQ_PARAMS['filter'])})
        # Request a response from the data url
        response = requests.get(__REQ_URL, params=req_params).text
        # Get the number of all pages containing the information
        page_all = int(re.search(re.compile(
            r'var.*?{pages:(\d+),data:.*?'), response).group(1))

        # Go through all the pages to get all the stock information this
        # url has to offer
        for pg in range(1, page_all + 1):
            req_params.update({'p': pg})
            if pg > 1:
                response = requests.get(__REQ_URL, params=req_params).text
            report_data = report_data.append(
                extract_data(response), ignore_index=True, sort=False)

    format_dtypes(report_data,
                  skip_cols=['scode', 'reportdate', 'hycode', 'companycode',
                             'sname', 'publishname', 'mkt', 'noticedate',
                             'eutime'],
                  inplace=True)

    # Remove time strings from dataframe
    str_cols = report_data.dtypes.loc[
        report_data.dtypes == np.dtype('O')].index.tolist()
    for col in str_cols:
        report_data.loc[:, col] = report_data.loc[:, col].str.replace(
            r'T\d\d:\d\d:\d\d', '', case=True)

    # Set the indices to columns with unique and non-null values
    for col in ('reportdate', 'noticedate', 'eutime'):
        report_data[col] = pd.to_datetime(report_data[col],
                                          format='%Y/%m/%d').dt.date

    if save_dir is not None:
        report_data.to_pickle(os.path.join(save_dir, f'{report_type}.pkl'))
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        xlsx_writer = pd.ExcelWriter(
            os.path.join(save_dir, f'{report_type}.xlsx'), engine='xlsxwriter',
            datetime_format='yyyy/mm/dd', date_format='yyyy/mm/dd')
        # Convert the dataframe to an XlsxWriter Excel object.
        report_data.reset_index(drop=True).to_excel(
            xlsx_writer, sheet_name=report_type, index=False)

        # Get the xlsxwriter workbook and worksheet objects.
        workbook = xlsx_writer.book
        worksheet = xlsx_writer.sheets[report_type]
        special_cols = [('00000#', 'scode'),
                        ('0000#', 'hycode'),
                        ('0000000#', 'companycode'),
                        ('0#.000000000', 'tsatz'),
                        ('0#.000000000', 'tdetz'),
                        ('0#.000000000', 'ld'),
                        ('0#.000000000', 'zcfzl'),
                        ('0#.000000000', 'tystz'),
                        ('0#.000000000', 'yltz'),
                        ('0#.000000000', 'sjltz'),
                        ('0#.000000000', 'sjlktz')]
        data_cols = report_data.columns.tolist()
        # Set the column width and format.
        for sc in special_cols:
            if sc[1] in data_cols:
                cformat = workbook.add_format({'num_format': sc[0], })
                worksheet.set_column(data_cols.index(sc[1]),
                                     data_cols.index(sc[1]),
                                     None, cformat)

        for ci in range(data_cols.index('eutime') + 1, len(data_cols)):
            if ('_tb' in data_cols[ci]) or ('_zb' in data_cols[ci]):
                cformat = workbook.add_format({'num_format': '0#.000000000', })
                worksheet.set_column(ci, ci, None, cformat)
            elif data_cols[ci] not in [s[0] for s in special_cols]:
                cformat = workbook.add_format({'num_format': '0#.00', })
                worksheet.set_column(ci, ci, None, cformat)
        # Note: It isn't possible to format any cells that already have a
        # format such as the index or headers or any cells that contain dates
        # or datetimes.
        xlsx_writer.save()

    return report_data


def extract_data(response):
    items = json.loads(re.search(re.compile(
        'var.*?data: (.*),font', re.S), response).group(1))
    font_mapping = json.loads(re.search(re.compile(
        'var.*?"FontMapping":(.*)}}', re.S), response).group(1))
    digit_mapping = {}
    for d in font_mapping:
        digit_mapping[d['code']] = str(d['value'])
    result = pd.DataFrame(items, columns=items[0].keys()).replace(
        digit_mapping, regex=True)
    result = result.replace('^-$', 0, regex=True)
    return result


if __name__ == '__main__':
    data = []
    for st in SHEET_TITLES:
        data.append(get_reports(st, 2013, 2019,
                    save_dir=os.path.join(os.path.dirname(__file__), 'data')))
        print(data[-1])
