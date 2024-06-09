import json
import time
import requests
import numpy as np
import pandas as pd
from openai import OpenAI

# To access GPT API
GPT_API_KEY = "<YOUR_API_KEY>"

# SmartThings settings to send REST API calls: - to check validity of GPT generate rules
SmartThings_Location_ID = "<YOUR_ST_LOCATION_ID>"
SmartThings_Auth_Token = "<YOUR_ST_Auth_Token>"
Rules_API_url = "https://api.smartthings.com/v1/rules?"
params = {
    "locationId": SmartThings_Location_ID
}
auth_token = SmartThings_Auth_Token
headers = {
    "Authorization": f"Bearer {auth_token}",
    "Content-Type": "application/json"
}

# inputs
# to get automation scenario and semantics
input_data_scenarios_file = '../input/ground_truth_rule_semantic.xlsx'
df_automation_scenarios = pd.read_excel(input_data_scenarios_file,sheet_name=0)
all_rules_list = df_automation_scenarios.app_name.tolist()

# output file
prompt_output_data_file = '../output/prompt_resp_rule_syntax_results.xlsx'
df = pd.DataFrame(columns=["app_name", "semantics", "GPT_Response", "Time", "Response_Code", "Response_Text"])
df.to_excel(prompt_output_data_file, index=False)

# prototype context free grammar for SmartThings Rules API
grammar_V4 = '(J) --> { "name": "(String)", "actions": [(Acs)] } (Acs) --> {(Ac)} | {(Ac)}, (Acs) (Ac) --> (IF)| (IF), "else": [(ThenAcs)] | "every" : {(EV)} (IF) --> "if" : {(LogCon), "then" : [(ThenAcs)]} (LogCon) --> "and": (AND) | "or": (OR) | "not" : (NOT) (ThenAcs) --> {(ThenAc)} | {(ThenAc)}, (ThenAcs) (ThenAc) --> "sleep" : {(SL)} | "command" : {(CM)} (AND) --> [ (LogOps) ] (OR) --> [ (LogOps)] (LogOps) --> (LogOp),(LogOp)|(LogOp),(LogOps) (LogOp) --> {(LogCon)} | {(Condition)} (NOT) --> {(LogCon)} | {(Condition)} (Condition) --> (Eq)| (Gt) | (GEq) | (Lt) | (LEq) | (Bt) (Eq) --> "equals":{ "left":{(LOp)}, "right":{(ROp)} } (Gt) --> "greaterThan":{ "left":{(LOp)}, "right":{(ROp)} } (GEq) --> "greaterThanOrEquals":{ "left":{(LOp)}, "right":{(ROp)} } (Lt) --> "lessThan":{ "left":{(LOp)}, "right":{(ROp)} } (LEq) --> "lessThanOrEquals":{ "left":{(LOp)}, "right":{(ROp)} } (Bt) --> "between" : (TimeBetween)|"between" : (DeviceBetween) (TimeBetween) --> "between" : { "value" : {(Time)}, "start": {(TimeOff)}, "end":{(TimeOff)}} (DeviceBetween) --> "between" : { "value" : {(Device)}, "start": {(Int)}, "end":{(Int)}} (LOp) --> (Device)|(Loc)|(DateTime) (Device) --> "device" : { "devices":[(DIDArr)], "component" : "main", "capability": "(String)", "attribute":"(String)"} (DIDArr) --> "(String)"|"(String)",(DIDArr) (Loc) --> "location" : {"attribute" : "mode"} (Time) --> "time":{"reference":(TimeRef)} (TimeOff) --> "time":{"reference":(TimeRef),"offset":{"value":{("integer":(Int))}, "unit":"(TimeUnit)"}} (DateTime) --> "datetime":{"reference":"(TimeRef)", "timeZoneId":"(String)", "locationId":"(String)","daysOfWeek":"(WeekDay)","year":(Int), "month":"(Month)", "day":"(Date)", "offset":{"value":{(ROp)},"unit":"(TimeUnit)"}} (TimeRef) --> "Now" | "Midnight" | "Sunrise" | "Noon" | "Sunset" (WeekDay) --> "Sun" | "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" (Month) --> "(Int) [1..12]" (Date) --> "(Int) [1..31]" (ROp) --> "boolean":(Bool)|"integer":(Int)|"string":"(String)" (SL) --> "duration":{"value":{(ROp)}, "unit":"(TimeUnit)"} (TimeUnit) --> "Second" | "Minute" | "Hour" | "Day" | "Week" | "Month" | "Year" (CM) --> "devices":[(DIDArr)]|"commands":[(CmdsArr)] (CmdsArr) --> (CmdArrwoArgs)|(CmdArrwArgs),(CmdsArr) (CmdArrwoArgs) --> {"component" : "main", "capability": "(String)", "command":"(String)"} (CmdArrwArgs) --> {"component" : "main", "capability": "(String)", "command":"(String)", "arguments":[(ArgArr)]} (ArgArr) --> (ROp)|(ROp),(ArgArr)'

def callGPT(prompt, desc):
    respnse_text = None
    response_gpt = None
    print("_----********************************************************************************-----")
    print("_----************************* API request "+ desc +"********************************-----")
    start_time = time.time()
    client = OpenAI(api_key= GPT_API_KEY)
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        stream=False,
    )
    neew_response_gpt = stream.choices[0].message.content
    print(neew_response_gpt)
    end_time = time.time()
    duration = end_time - start_time
    try:
        json_body_response_gpt = json.loads(neew_response_gpt)
        api_response = requests.post(Rules_API_url, params=params, headers=headers,
                                     json=json_body_response_gpt)
        code = api_response.status_code
        respnse_text = api_response.text
        print(code)
        print(type(code))
        print(respnse_text)
        response_gpt = json_body_response_gpt
        return duration, code,respnse_text, response_gpt
    except ValueError:
        print('2nd No API request ValueError')
        if response_gpt is not None:
            response_gpt = response_gpt.replace("\n", "")
        return duration, None, respnse_text, response_gpt


commandToContint = True
not_success_list = []
skip_app_list = []
i = 0
for app_name in all_rules_list:
    print("_----*************************  START ********************************-----")
    if app_name is not np.nan:
        record_semantics = df_automation_scenarios.loc[df_automation_scenarios['app_name'] == app_name]
        semantics = record_semantics['Ground_Truth_v2'].values[0]
        print(app_name)
        print(semantics)

        if commandToContint:
            try:
                response = None
                json_response = Noneduration = None
                duration = None
                if semantics is not np.nan: # if ground truth is available
                    actual_task = semantics.replace("\n", "")
                    print(actual_task)
                    prompt_update = grammar_V4 + ' Please write JSon code for' + actual_task + ', using above context free grammar. Please don not write any other text at fronT or end of JSON, e.g. ```json ```'

                    print("_---------------------------prompt update-------------------------------------")
                    print(prompt_update)
                    print("_---------------------------------------------------------------------------")
                    if app_name not in skip_app_list:
                        # call GPT first time
                        #################################################################################3
                        duration, code, respnse_text, response_gpt = callGPT(prompt_update, "first")
                        #################################################################################3
                        if code == 422:
                            json_str = json.dumps(response_gpt)
                            fix_422_new_prompt = "remove additional text outside json Structure. if 'else' array is outside 'if' object, remove it and add next to 'then' inside 'if'" + json_str + " Please don not write any other text at fronT or end of JSON, e.g. ```json ```"
                            duration, code, respnse_text, response_gpt = callGPT(fix_422_new_prompt, "second fix else")
                        #################################################################################3
                    df = pd.DataFrame(
                        [[app_name, semantics, response_gpt, duration,code, respnse_text ]])
                    with pd.ExcelWriter(prompt_output_data_file, mode="a", engine="openpyxl",
                                        if_sheet_exists="overlay") as writer:
                        df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False,
                                    header=False)
                print("_----*************************  END ********************************-----")

            except IndexError:
                print('No capabilities')
            except ValueError:
                print('No ValueError')


