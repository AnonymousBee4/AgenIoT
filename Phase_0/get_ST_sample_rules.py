import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
from chromedriver_py import binary_path

svc = webdriver.ChromeService(executable_path=binary_path)
browser = webdriver.Chrome(service=svc)
############################################################################
ST_Rules_Samples = 'https://github.com/SmartThingsDevelopers/Sample-RulesAPI/tree/master/Sample%20JSON%20Rules'

# output
rulesytax_output_data_file = '../output/smarthings_rules_samples_dataset.xlsx'
df = pd.DataFrame(columns=["title", "Desc", "json_code"])
df.to_excel(rulesytax_output_data_file, index=False)

browser.get(ST_Rules_Samples)
time.sleep(15)

applet_page_response_eb = browser.page_source
applet_page_content_eb = BeautifulSoup(applet_page_response_eb, "html.parser")
table_body = applet_page_content_eb.find("tbody")

for row in table_body.contents:
    try:
        print(row)
        rowid = row['id']
        rowidsplits = rowid.split('-')
        if int(rowidsplits[2]) < 35:
            continue
        else:
            a_link = row.find('a', class_="Link--primary")
            a_link_href = a_link['href']
            title = a_link['title']
            browser.get('https://github.com/' + a_link_href)
            time.sleep(5)
            code_source = browser.page_source
            code_content = BeautifulSoup(code_source, "html.parser")
            json_code = code_content.find('div', class_='Box-sc-g0xbh4-0 eRkHwF')
            json_code_area = json_code.find('textarea')
            print(json_code_area.text)
            json_format = json.loads(json_code_area.text)
            print(json_format)
            desc = json_format['name']

            df = pd.DataFrame(
                [[title, desc, json_format]])  # , columns=["title", "Desc", "json_code"]
            with pd.ExcelWriter(rulesytax_output_data_file, mode="a", engine="openpyxl",
                                if_sheet_exists="overlay") as writer:
                df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False,
                            header=False)
    except KeyError:
        print('no id')


browser.close()


