import time
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
from chromedriver_py import binary_path

svc = webdriver.ChromeService(executable_path=binary_path)
browser = webdriver.Chrome(service=svc)
############################################################################

URL_Production_Capability = 'https://developer.smartthings.com/docs/devices/capabilities/capabilities-reference'

# output
output_data_file = '../output/prod_capabilities.xlsx'
df = pd.DataFrame(columns=["capabilitiy", "Json_URL", "Json_Content"])
df.to_excel(output_data_file, index=False)
app_name_list = []

browser.get(URL_Production_Capability)
time.sleep(15)
cap_page_response = browser.page_source
cap_page_content = BeautifulSoup(cap_page_response, "html.parser")
cap_titles_divs = cap_page_content.find_all("div", class_="titleContainer_JK7b")
for cap_divs in cap_titles_divs:
    cap_divs_content = BeautifulSoup(str(cap_divs), "html.parser")
    link_a = cap_divs_content.find("a", class_="titleLink_RK62")
    title_div = cap_divs_content.find("div", class_="title_eAs_")
    cap_title = title_div.text
    json_link = link_a['href']
    browser.get(json_link)
    time.sleep(10)
    cap_json_response = browser.page_source
    cap_json_response_content = BeautifulSoup(cap_json_response, "html.parser")
    json_link_content = cap_json_response_content.text
    df = pd.DataFrame([[cap_title, json_link, json_link_content]])  # , ["capabilitiy", "Json URL", "Json Content"])
    with pd.ExcelWriter(output_data_file, mode="a", engine="openpyxl",
                        if_sheet_exists="overlay") as writer:
        df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row,
                    index=False, header=False)
browser.close()