import time
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
from chromedriver_py import binary_path

svc = webdriver.ChromeService(executable_path=binary_path)
browser = webdriver.Chrome(service=svc)
############################################################################

URL_IoTbench = 'https://github.com/IoTBench/IoTBench-test-suite/tree/master/smartThings/smartThings-contexIoT/smartThings-contextIoT-official-and-third-party'
Prefix_URL = 'https://github.com/'

# output
output_data_file = '../output/smartapp_dataset.xlsx'
df = pd.DataFrame(columns=["app_name", "URL", "Desc"])
df.to_excel(output_data_file, index=False)
app_name_list = []

browser.get(URL_IoTbench)
time.sleep(15)
applet_page_response = browser.page_source
applet_page_content = BeautifulSoup(applet_page_response, "html.parser")


links = applet_page_content.find_all("a", class_="Link--primary")
set_links = set(links)
for link in set_links:
    name_array = link['href'].split('/')
    name = name_array[len(name_array)-1]
    if name not in app_name_list:
        app_name_list.append(name)
        print(name)
        print(link['href'])
        app_link = 'https://github.com/'+ link['href']
        browser.get(app_link)
        time.sleep(15)
        applet_page_response = browser.page_source
        applet_page_content = BeautifulSoup(applet_page_response, "html.parser")
        span_list = applet_page_content.find_all("span", class_="pl-c1")
        for spanl in span_list:
            if spanl['data-code-text'] == 'description':
                parent_code = spanl.parent
                parent_code_content = BeautifulSoup(str(parent_code), "html.parser")
                desc_spans_parent = parent_code_content.find_all("span", class_="pl-s")
                try:
                    desc_spans_parent_code_content = BeautifulSoup(str(desc_spans_parent[0]), "html.parser")
                    desc_spans = desc_spans_parent_code_content.find_all("span", attrs={'class': None})
                    for desc_span in desc_spans:
                        try:
                            if len(desc_span.attrs) == 1:
                                if desc_span['data-code-text']:
                                    if len(desc_span['data-code-text']) >15:
                                        print(desc_span['data-code-text'])
                                        app_desc = desc_span['data-code-text']
                                        df = pd.DataFrame([[name, app_link, app_desc]])  # , columns=["app_name", "URL", "Desc"])
                                        with pd.ExcelWriter(output_data_file, mode="a", engine="openpyxl",
                                                            if_sheet_exists="overlay") as writer:
                                            df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row,
                                                        index=False, header=False)
                        except KeyError:
                            print('No data-code-text')
                except IndexError:
                    print('index error')

browser.close()
print(app_name_list)