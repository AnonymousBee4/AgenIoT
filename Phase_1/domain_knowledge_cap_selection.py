# Given a description determine the domain knowledge should be given in prompt for ChatGPT
import pandas as pd
import time
from openai import OpenAI

# To access GPT API
GPT_API_KEY = "<YOUR_API_KEY>"

# inputs
data_set_file = '../input/ground_truth_capabilities.xlsx'
df_name_desc = pd.read_excel(data_set_file,sheet_name=0)

prod_cap_data_file = '../input/prod_cap_summaries.xlsx'
df_prod_cap = pd.read_excel(prod_cap_data_file,sheet_name=0)
prod_cap_summary_list = df_prod_cap.Summary.tolist()

# output
prompt_output_data_file = '../output/prompt_resp_selected_capability_result.xlsx'
df = pd.DataFrame(columns=["app_name", "Desc", "GPT_Response", "time"])
df.to_excel(prompt_output_data_file, index=False)

response = None
login_status = False
domain_knowledge = ','.join(prod_cap_summary_list)

tutorial = 'Tutorial: Learn how to identify capabilities related to the automation scenario, given all the available production capabilities as domain knowledge. We provide two examples, with expected output and the chain of thoughts involved. '\
           'Capability Format Description on how to read production capabilities: The general format of a capability is “<capabilityName>=[attributes:[<attributeName>(<attributeType>)=[<possibleValues>])], [commands: [<commandName>(arguments=[<argumentName> (<argumentType>) =[<possibleValues>]])]]]”. For example, accelerationSensor=[attributes: [’acceleration(string)= [active,inactive]’], commands:[] and airConditionerFanMode=[attributes: [’fanMode(string)’, ’supportedAcFanModes(array)’], commands: [”setFanMode(arguments = [’fanMode(string)’])”]] are two capabilities.  Each capability has a name <capabilityName> (e.g., accelerationSensor), a set of attributes (attributes:[]) and a set of commands (commands:[]). Each attribute has a name <attributeName> (e.g.,acceleration) a data type <attributeType> (e.g., String), and optionally a set of possible values [<possibleValues>] (e.g., [active,inactive]). Each command has a name <commandName> (e.g., setFamMode ) and a set of arguments. Each argument has a name < argumentName > (e.g., fanMode), a data type (e.g.,String) and possible values. If certain information is not defined for the capability that is shown in empty brackets. '\
           'Production Capabilities: Follow the how to read guide and memories the following capabilities. '+ domain_knowledge + '' \
           'Special Instructions to map words in automation scenario to production capabilities: To identify the most appropriate <capabilityName> for a given new automation scenario, LLM should study the words describing state changes and commands in the automation scenario and map them to the attribute and commands vocabulary in the production capabilities. When choosing from the given capabilities (in domain knowledge), if the scenario specifies a status change of device or service, then LLM should look for the vocabulary used in the attribute section of the capabilities to select the most suitable capability. If the scenario specifies involvement of command executions, then LLM should look for the vocabulary used in the commands section of the capabilities supported by the platform. The output format is a list of <capabilityName>s. This list should strictly use the most appropriate <capabilityName> from the production capabilities vocabulary. If a matching capability is not found, do not add imaginative capabilities.'\
           'Output format: [<capabilityName_1>, <capabilityName_2>, ... , <capabilityName_N>]'\
           'Task1 Start: Automation Scenario for Task1: This app uses three virtual tiles and any number of open/close sensors as well as lights.  One virtual tile will be turned on by UBI, which still triggers the program to run.  ' \
           'Three things will happen: A.) If any doors are open, the second virtual tile will be turned on.  This will cause UBI to warn that a door is open. B.) If any windows are open, the third virtual tile will be turned on.  This will cause UBI to warn that a window is open. C.) after a five-minute wait, all specified ' \
           'lights and the three virtual devices will be turned off." Use domain knowledge of Internet of things.' \
           'Chain of Thoughts for Task1: This automation involves three types of objects, i.e., door/window, lights, and virtual tiles. The scenario checks if doors/windows are in open or closed states. That means need to find an attribute with given states as possible values. The  “contactSensor” capability  has “contact” attribute with “open” and “closed” as possible values. Next, the scenario performs actions to change the status of switches to “on” or “off” states. To achieve this need to find a capability which provides the commands “on()” or “off()”. The switch capability provides the two commands. Hence, the two capabilities, contactSensor and switch are selected from the platform supported capabilities.'\
           'Result for Task1: [contactSensor, switch] Task1 End' \
           'Task2 Start: Automation Scenario for Task2: Unlocks the door when you arrive at home.' \
            'Chain of Thoughts for Task2: This automation involves a door lock and a presence sensor. The user’s arrival or presence (synonym to arrival) is detected by using a presence sensor. The “presenceSensor” capability of SmartThings platform has an attribute called “presence” with two possible state values “present” and “not present”. To perform lock/unlock actions on the door, we need to find a capability that supports lock/unlock commands. The “lock” capability has two commands “lock()” and “unlock()”. Therefore, the two capabilities, i.e., lock and presenceSensor. are selected from the platform supported capabilities. '\
            'Result for Task2:[lock, presenceSensor] Task2 End'


commandToContint = True

for i_name_desc in df_name_desc.index:
    cap_list = None
    app_name = df_name_desc['app_name'][i_name_desc]

    if commandToContint:
        desc = df_name_desc['Desc'][i_name_desc]
        print(app_name)
        print(desc)

        # prompt GPT for the description
        prompt_task = 'Actual Task: Identify capabilities related to the new automation scenario: "' + desc

        prompt_update = tutorial + ' '+prompt_task + ' ' "Please do not write any other text"
        print(prompt_update)
        print("_---------------------------------------------------------------------------")
        start_time = time.time()
        client = OpenAI(api_key=GPT_API_KEY)
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt_update}],
            stream=False,
        )
        response = stream.choices[0].message.content
        end_time = time.time()
        duration = end_time - start_time
        print("_----******************************************************************-----")
        print(response)
        print(type(response))
        df = pd.DataFrame(
        [[app_name, desc, response, duration]])  # , columns=["app_name", "Desc", "GPT_Response"])
        with pd.ExcelWriter(prompt_output_data_file, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
            df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False, header=False)

