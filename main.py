import pandas as pd
from china_company_info import ChinaCompanyInfo
csi = ChinaCompanyInfo()
"""csi.get_table(0, 2013, 2017)
csi.get_table(1, 2013, 2017)
csi.get_table(2, 2013, 2017)
"""
csi.load_dataframe(0)
csi.load_dataframe(1)
csi.load_dataframe(2)

csi.stock_ind()
csi.clean_dataframe()
csi.industry_to_number(0)
csi.industry_to_number(1)
csi.industry_to_number(2)
data_start = csi.df_fr[0].columns.get_loc('publishname') + 1
all_df = pd.merge(  pd.merge(csi.df_fr[0], csi.df_fr[1].iloc[:,data_start:], how = 'inner', left_index = True, right_index = True),
                    csi.df_fr[2].iloc[:,data_start:], how = 'inner', left_index = True, right_index = True).copy()
print(all_df.iloc[all_df.index.get_level_values(1) == '2017-12-31'])