import time
import pandas as pd
from openai import OpenAI

# To access GPT API
GPT_API_KEY = "<YOUR_API_KEY>"

# selected capabilities by GPT
gpt_res_cap_data_file = '../input/ground_truth_capabilities.xlsx'
df_gpt_cap_gt = pd.read_excel(gpt_res_cap_data_file,sheet_name=0)

prod_cap_data_file = '../input/prod_cap_summaries.xlsx'
df_prod_cap = pd.read_excel(prod_cap_data_file,sheet_name=0)
prod_cap_list = df_prod_cap.cap_ID.tolist()

# to get automation scenario and ground truth
input_data_scenarios_file = '../input/ground_truth_rule_semantic.xlsx'
df_automation_scenarios = pd.read_excel(input_data_scenarios_file,sheet_name=0)
automation_scenario_list = df_automation_scenarios.app_name.tolist()

prompt_output_data_file = '../output/prompt_resp_rule_semantic_results.xlsx'
df = pd.DataFrame(columns=["app_name", "Desc", "GPT_Response","Ground_Truth","Domain_Kdg", "time"])
df.to_excel(prompt_output_data_file, index=False)

tutorial = "Tutorial: Write all the rules with the correct rule semantics to achieve the automation described in the Acutal Task automation scenario. The output rule semantics should be one of the listed rule semantics and should strictly follow one of the defined formats of trigger condition or action semantics. The GPT response should not include any other text or explanations other than the rule semantics. To identify the correct semantics of trigger conditions and actions, in particular the devices, capabilities, attributes, commands and accepted values, please refer to the domain knowledge given. The rule format description and domain knowledge description help LLM to understand the content in domain knowledge and rule semantics. In the below we provide three example tasks and chain of thoughts involving determining the rules for the given automation scenarios. LLM should learn from the examples, how to extract information from a given automation scenario and write the correct rule semantics using the information in the domain knowledge and as instructed in rule semantic formats, trigger condition semantic formats and action semantic format. Additionally, to combine rules follow the “combining rules” instructions. "

rule_semantics_and_examples =   "Domain Knowledge Description: How to read domain knowledge: The general format of a capability is “<capabilityName>=[attributes:[<attributeName>(<attributeType>)=[<possibleValues>])], [commands: [<commandName>(arguments=[<argumentName> (<argumentType>) =[<possibleValues>]])]]]”. For example, accelerationSensor=[attributes: [’acceleration(string)= [active,inactive]’], commands:[] and airConditionerFanMode=[attributes: [’fanMode(string)’, ’supportedAcFanModes(array)’], commands: [”setFanMode(arguments = [’fanMode(string)’])”]] are two capabilities. I'll explain how to read domain knowledge. Each capability has a name <capabilityName> (e.g., accelerationSensor), a set of attributes (attributes:[]) and a set of commands (commands:[]). Each attribute has a name <attributeName> (e.g.,acceleration) a data type <attributeType> (e.g., String), and optionally a set of possible values [<possibleValues>] (e.g., [active,inactive]). Each command has a name <commandName> (e.g., setFamMode ) and a set of arguments. Each argument has a name < argumentName > (e.g., fanMode), a data type (e.g.,String) and possible values. If certain information is not defined for the capability that is shown in empty brackets. " \
           "Rule Semantics Formats: RS_Format_1 (simple if-then rule): [IF trigger_condition, THEN action], RS_Format_2 (with else): [IF trigger_condition, THEN action, ELSE action] , RS_Format_3 (multiple actions): [IF trigger_condition, THEN action_1 and action_2, …, action_n], RS_Format_4 (multiple triggers): [IF trigger_condition_1 and/or  trigger_condition_2, …trigger_condition_m, THEN action], RS_Format_5 (with wait): [IF trigger_condition, THEN wait(`x minutes`) and action], RS_Format_6 (nested rules): [IF trigger_condition, THEN action and  [IF trigger_condition, then action2]] " \
           "Rule format Description: The general format of  IoT rule is if-this-then-that. In particular, if this trigger condition satisfies, then perform that action. The rule format should be selected based on the information in the automation scenario. The simplest rule format is RS_Format_1 with a single trigger and a single action. If the automation scenario describes actions for the case otherwise, RS_Format_2 can be used with “ELSE” keyword. If the automation scenario specifies multiple actions to perform when the trigger satisfies, then as in RS_Format_3 use, “and” keyword to combine them. If the automation scenario specifies multiple trigger conditions, they can be combined using the “and” or “or’ keywords, as in RS_Format_4. If the automation scenario describes a delay or waiting period, then use the “wait” keyword with the value in “minutes/seconds/hours” as in RS_Format_5. If the automation scenario specifies nested conditions and actions use RS_Format_6. Additionally, if the automation scenario describes the trigger attribute (e.g., x) to be between two values (i.e., value_1 and value_2), then use the semantics (value_1 < x < value_2)."\
           "Trigger Condition Semantics Formats: From the automation description, LLM should identify the specific capabilities, their attributes names,  state values (<possible values>), commands and their arguments from the domain knowledge provided. If the automation scenario includes the device, then use TC_Format_2. If it also includes the room where the device is located, then use TC_Format_3. Otherwise, use TC_Format_1, and refer to the attribute information in the identified capabilities in the domain knowledge. The \"value\" should be only using the information in the possible values, or a value belongs to the attribute type. If the trigger condition involves time schedules or periods (LLM should use its intuition to recognize when automation scenario refers to a time period.), then use TC_Format_4 or TC_Format_5 or TC_Format_6. To specify the time, LLM can use the absolute time as in automation scenario or if related the keywords (“midnight”, “sunrise”, “noon”, “sunset”). The automation scenario may or may not include the trigger device (e.g., light) and device location/room (e.g., kitchen). Therefore, the trigger condition should take one of the following formats. TC_Format_1: <capability_name.attribute_name == “possible value“>, TC_Format_2:  <device.capability_name.attribute_name == “value“>, TC_Format_3: <room.device.capability_name.attribute_name == “value“>, TC_Format_4: <now.time==”specified time”>, TC_Format_5: <”start time”<now.time < “end time”>, TC_Format_6: <now.day==”specified day”>. The possible values for now.day are \"Sun\", \"Mon\", \"Tue\", \"Wed\", \"Thu\", \"Fri\", or \"Sat\""\
           "Action Semantics Formats: From the automation description, LLM should identify the specific capabilities, commands, and argument values (if any). To identify the correct semantics of the trigger conditions, refer to the commands of the capabilities from the domain knowledge provided. The action should take one of the following formats. . If the automation scenario includes the device, then use AC_Format_2. If it also includes the room where the device is located, then use AC_Format_3. Otherwise, use AC_Format_1  or AC_Format_4  and refer to the command information in the identified capabilities in the domain knowledge. If the automation scenario specifies a waiting/delay period  (for example identified by words “for x seconds”, “after few minutes”, “for a period”, “for a while”), then use the AC_Format_5. AC_Format_1: <capability_name.command_name()>, AC_Format_2: <device.capability_name.command_name()>, AC_Format_3: <room.device.capability_name.command_name()>, AC_Format_4:   <capability_name.command_name(arg1_value, …, argN_value)>, AC_Format_5: <wait(“specified period”)>  If the command has arguments, then the argument values can be appended to the argument_name using the dot operator. For example, let's take domain knowledge “setLevel(arguments = ['level(integer)', 'rate(integer)’])”) of switchLevel capability, then the action semantics would be \"switchLevel.setLevel(100, 10)\". Make sure the command argument select values matching to given data type." \
           "Identify when to use wait action (AC_Format_5): There are two main occasions. First, to define waiting or delay periods. Second, to check if the trigger condition remains for a while. The first case can be ientified with phrases similar to 'wait for ... seconds', '... after x minutes', and 'after ... seconds'. The second case can be identified with phrases similar to “stays ... for x seconds”, 'left .. for a period', “when ... for few minutes”, “few minutes ... later”, and '...for sometime', that implies a waiting after certain condition is reached. To add semantics to the rule, use the wait(“period”) action. If the amount of time to wait is given replace “period” with that. Otherwise, default value is “x” minutes. Also, if automation scenario requires to check the trigger condition remains after the wait period, then use the RS_Format_6 as described in “Example for Case 2”"\
           "Combining Rules: The rule semantics RS_Format_2, RS_Format_5, and RS_Format_6 can be used to combine multiple rules: We identify two cases where multiple rules can be combined as one rule.  Case1: If the automation scenario specifies to perform action A when the condition is True and if otherwise, perform Action B. Then use the Rule semantics RS_Format 2 (with else). Example for Case1: If variable x is greater than 10 perform action A, otherwise perform action B. [If x > 10 THEN A(), ELSE B()]. Case2: If the automation scenario specifies to perform action A when the condition is True and remains for few minutes. For this rule semantics RS_Format_5(with wait) and RS_Format_6 (nested) can be used. Example for Case2: If variable x is greater than 10 for 5 minutes, then perform a. [IF x > 10, THEN wait(“5 minutes”) and [IF x> 10, THEN A()]]. Case 3: If the automation scenario specifies to perform action A when the condition is True. Then wait for 5 minutes, and perform B. Then use the Rule semantics RS_Format_5. Example for Case 3: If variable x is greater than 10, perform action A. Then wait for 5 seconds and perform action B. [IF  x > 10, THEN A() and wait(“5 seconds”) and B()]]"\
           "Task1 START: IF a door or a window opens, turn on a virtual switch. After 5 minutes turn off the switch."\
           "Domain Knowledge for Task 1: contactSensor=[attributes: ['contact(string)=[closed,open]'], commands: []], switch=[attributes: ['switch(string)=[on,off]'], commands: [\"off(arguments = '[]')\", \"on(arguments = '[]')\"]]" \
           "Chain of Thoughts for Task1: This automation involves three devices, i.e., a door, a window and a virtual switch. The phrase “door or a window opens” explains trigger conditions. To check the open or close states of the trigger devices, door and window, contact sensors are used. According to the domain knowledge, contactSensor capability has an attribute called “contact” which holds possible values “open” or “closed”. Since we also know the device, these two trigger conditions can be formatted using TC_Format_2. The phrase “turn on a virtual switch” explains an action condition. To perform actions on or off switches are used. According to the domain knowledge, “switch” capability has two commands on() and off(). This action can be formatted using AC_Format_2. The phrase “after 5 minutes turn off the switch” explains two additional actions to the same rule. The sub phrase “after 5 minutes” implies a sleep period. This can be specified in the rule using wait() action. The argument is “5 minutes”. The sub phrase “turn off switch” can be specified using the off() command of the “switch” capability. These trigger conditions and actions can be formatted into a single rule by combining rule formats RS_Format_3, RS_Format_4, and RS_Format_5 as follows. The vocabulary for the rule is taken from the capability knowledge."\
           "Rules for Task1: [IF door.contactSensor.contact==”open” or window.contactSensor.contact==”open”, THEN virtualSwitch.switch.on() and wait(“5 minutes”) and  virtualSwitch.switch.off()”]"\
           "Task2 START: Automation Scenario for Task2: Unlocks the door when you arrive at your location and change the mode to home and adjust the heater and AC based on current temperature. Turn on the kitchen lights only between sunset and sunrise. Notify me when the location mode changes to home. " \
           "Domain Knowledge for Task 2: presenceSensor=[attributes: ['presence(string)=[present,not present]'], commands: []], lock=[attributes: ['lock(string)=[locked,unknown,unlocked,unlocked with timeout,not fully locked]'], commands: [\"lock(arguments = '[]')\", \"unlock(arguments = '[]')\"]], switch=[attributes: ['switch(string)=[on,off]'], commands: [\"off(arguments = '[]')\", \"on(arguments = '[]')\"]], temperatureMeasurement=[attributes: ['temperature(number)'], commands: []], notification=[attributes: [], commands: [\"deviceNotification(arguments = ['notification(string)'])\"]]"\
           "Chain of Thoughts for Task2: This automation involves five types of devices, i.e., door lock, presence sensor, heater, AC, and lights. The door lock is identified by the phrase “unlocks the door”. The presence sensor is identified by the phrase ”When you arrive”. The presence sensor is the trigger device. The door lock is an action device. When the status of the presence sensor attribute named \"presence\" changes to “present”, perform the unlock() command of the lock capability and change the status of the location mode to home. This requires one rule. This rule requires you to notify the user. Therefore, add another action to send SMS to a given phone number. Additionally, the automation description wants to perform on() or off() commands on the devices AC and heater, using the switch capability. When assigning the values for the heater and AC think about the safety use of the device. This can be achieved with two rules. If the user arrives at home between sunset and sunrise, then turn on the kitchen lights. This requires another rule. Overall, this automation requires only four rules. The trigger conditions of these rules use TC_Format_1, and actions use AC_Format_3 depend on available data in this scenario. The used rule formats are RS_Format_3 and RS_Format_4. The vocabulary for the rule is taken from the capability knowledge." \
           "Rules for Task2: [If presenceSensor.presence==”present”, THEN door.lock.unlock() and locationMode.setMode(\"home\") and notification.deviceNotification(”mode changed to home”) ] [IF presenceSensor.presence==”present” and  temperatureMeasurement.temperature >= “desired_temperature”, THEN AC.switch.on() and heater.switch.off() ] [IF presenceSensor.presence==”present” and temperatureMeasurement.temperature <= “desired_temperature”, THEN AC.switch.off() and heater.switch.on() ] [IF presenceSensor.presence==”present” and “sunset” <= now.time <= “sunrise”, THEN kitchen.light.switch.on() ] " \
           "Task3 START: Automation Scenario for Task3: Bathroom light turns on when both doors are closed, off ten minutes later or when one or both doors are opened. " \
           "Domain Knowledge for Task 3: contactSensor=[attributes: ['contact(string)=[closed,open]'], commands: []], switch=[attributes: ['switch(string)=[on,off]'], commands: [\"off(arguments = '[]')\", \"on(arguments = '[]')\"]]"\
           "Chain of Thoughts for Task 3: This automation involves two types of devices, i.e., light and door contact sensor. This automation requires three rules. The trigger of the first rule is identified by the phrase “when both doors are closed”. It means when the contact sensors of the two doors are changed to closed state then perform the action. The action of the first rule is identified by the phrase “Bathroom light turns”. It means to change the status of the bathroom light to on. The second rule is identified by the phrase “off ten minutes later”. The trigger of the second rule is to wait for ten minutes after the outcome of the first rule. That means ten minutes after the change of door contact sensor to closed and change of bathroom light to turn on. The action of the second rule is to turn off the bathroom lights. The third rule is identified by the phrase “off … or when one or both doors are opened”. The trigger of the third rule is the state changes of one or both of the door contact sensors to open. The action of the third rule is to turn off the bathroom lights. To implement the trigger condition of the three rules, we choose the contactSensor  capability from the domain knowledge. It has one attribute named “contact” with two possible values “closed” and “open”. To implement the actions of the  rules we choose the switch capability from the domain knowledge. It provides two commands without any arguments named on() and off(). Additionally, to perform the delay action, we use the wait function with the wait period as the argument. The trigger conditions of these rules use TC_Format_2, and actions use AC_Format_4 depend on available data in this scenario.  The used rule formats are RS_Format_3, RS_Format_4 and RS_Format_5. The vocabulary for the rule is taken from the capability knowledge." \
           "Rules for Task3: [IF door1.contactSensor.contact==”closed” and door2.contactSensor.contact==”closed”, THEN bathroom.light.switch.on() and wait(”600 seconds”) and  bathroom.light.switch.off()] [IF door1.contactSensor.contact==open or door2.contactSensor.contact==”open”, THEN bathroom.light.switch.off()]"\
           "Task4 START: Automation Scenario for Task4: Turn light off when no motion is detected for a set period of time. "\
           "Domain Knowledge for Task 4: motionSensor=[attributes: [motion(string)=[active,inactive]'], commands: []],switch=[attributes: ['switch(string)=[on,off]'], commands: [\"off(arguments = '[]')\", \"on(arguments = '[]')\"]]"\
           "Chain of Thoughts Task 4: The phrase “turn light off” explains an action. The “light” is the device and the “turn off” refers to using a switch. Therefore, we use “switch” capability from the domain knowledge and format the action using the format AC_Format_2. The corresponding trigger condition is explained by the phrase “when no motion is detected.”. The motion can be detected by using a motionSensor. The motionSensor capability provides an attribute named “motion” with two possible values “active” and “inactive”. This trigger condition can be formatted using the TC_Format_1. The phrase “for a set period time” implies before performing the action, we should confirm that the preferred trigger condition remains for a time period. This remains condition may also refer in the automation scenario as “stay for a while”, “for a specified time ”, or “for x seconds”. In this case the rule can be formatted by combining the rule formats RS_Format_5 and RS_Format_6 as shown below. The amount of time specified for remain check is implemented using wait() action. Then a nested rule is used to recheck the trigger condition again and then perform the action. The vocabulary for the rule is taken from the capability knowledge."\
           "Rules for Task4: [IF motionSensor.motion == \"inactive\", THEN wait(\"x minutes\") and [IF motionSensor.motion == \"inactive\", THEN light.switch.off()]]"

def join_with_and(items):
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return ' and '.join(items)
    return ', '.join(items[:-1]) + ', and ' + items[-1]

commandToContint = True

for appName in automation_scenario_list:
    if commandToContint:
        print('.....................................................')
        print(appName)
        record_cap_gt = df_gpt_cap_gt.loc[df_gpt_cap_gt['app_name'] == appName]
        record_source = df_automation_scenarios.loc[df_automation_scenarios['app_name'] == appName]
        series_source_desc = record_source['Desc']
        series_source_index = series_source_desc.index[0]
        automation_scenario = series_source_desc[series_source_index]
        print(automation_scenario)
        series_semantic_gt = record_source['Ground_Truth']  # semantics ground truth
        series_semantic_gt_index = series_semantic_gt.index[0]
        semantic_ground_truth = series_semantic_gt[series_semantic_gt_index]
        print(semantic_ground_truth)

        if commandToContint:
            try:
                # selected capabilities in phase 1 part 1
                selected_cap_series = record_cap_gt['Ground_Truth']
                selected_cap_series_index = selected_cap_series.index[0]
                selected_capabilities = selected_cap_series[selected_cap_series_index]
                selected_capabilities = selected_capabilities.replace("[", '').replace("]", '')
                selected_cap_series_list = selected_capabilities.split(',')
                selected_cap_series_list = [s.lstrip() for s in selected_cap_series_list]

                cap_found = False
                domain_knowledge_list = []
                # if keyword not found in production_cap, then look into the keywords in json content of each prod_cap
                for p_cap in prod_cap_list:
                    i = len(selected_cap_series_list) - 1
                    while i >= 0:
                        if p_cap.lower() in selected_cap_series_list[i].lower():
                            record_p_cap = df_prod_cap.loc[df_prod_cap['cap_ID'] == p_cap]
                            series_p_cap = record_p_cap['Summary']
                            series_series_p_cap_index = series_p_cap.index[0]
                            prod_cap_json = series_p_cap[series_series_p_cap_index]
                            data = prod_cap_json
                            domain_knowledge_list.append(data)
                            i = 0
                            cap_found = True
                        i = i - 1
                domain_knowledge_str = join_with_and(domain_knowledge_list)
                print(domain_knowledge_str)
                actual_task = "Automation Description for Actual Task (strictly limit to the behavior in the scenario and vocabulary from capability domain knowledge.): " + automation_scenario
                prompt_update = tutorial + ' Domain Knowledge: ' + domain_knowledge_str +' '+ rule_semantics_and_examples +  actual_task + ' ' ". Please do not write any other text."
                print("_---------------------------------------------------------------------------")
                print(prompt_update)
                print("_---------------------------------------------------------------------------")
                response= None
                duration = None
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
                print("_----***************************** Result ***************************-----")
                print(type(response))
                processed_response = None
                try:
                    print(response)
                except IndexError:
                    print('error')
                print("_----******************************************************************-----")

                df = pd.DataFrame(
                    [[appName, automation_scenario, response, semantic_ground_truth, domain_knowledge_str, duration]])  # , columns=["app_name", "Desc", "GPT_Response"])
                with pd.ExcelWriter(prompt_output_data_file, mode="a", engine="openpyxl",
                                    if_sheet_exists="overlay") as writer:
                    df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False,
                                header=False)

            except IndexError:
                print('No capabilities')
            except ValueError:
                print('No ValueError')

