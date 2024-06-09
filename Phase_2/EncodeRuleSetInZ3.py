import re
from z3.z3 import Int, Bool, Solver, Implies, Not, sat, And, Real, Or, main_ctx
import pandas as pd

#GPT generated rules
gpt_generated_rules = 'output/prompt_resp_rule_semantic_result_example.xlsx'
gpt_generated_rules_file_read = pd.read_excel(gpt_generated_rules, sheet_name=0)
gpt_generated_rules_list = gpt_generated_rules_file_read.GPT_Response.tolist()
# domian knowledge
prod_cap_summary =  'input/prod_cap_summaries.xlsx'
prod_cap_summary_file_read = pd.read_excel(prod_cap_summary, sheet_name=0)
prod_cap_sum_list = prod_cap_summary_file_read.cap_ID.tolist()
#output
z3_output_file = 'output/z3_analysis_results.xlsx'
df = pd.DataFrame(columns=["ID","RuleSet", "Z3Formula", "Z3Result", "Model", "Constraints"])
df.to_excel(z3_output_file, index=False)

def utilInequalty(inequality,int_var,att_value, is_left ):
    new_variable = None
    if inequality == '>=':
        if is_left:
            new_variable = att_value >= int_var
        else:
            new_variable = int_var >= att_value
    elif inequality == '<=':
        if is_left:
            new_variable = att_value <=  int_var
        else:
            new_variable = int_var <= att_value
    elif inequality == '>':
        if is_left:
            new_variable = att_value > int_var
        else:
            new_variable = int_var > att_value
    elif inequality == '<':
        if is_left:
            new_variable = att_value <  int_var
        else:
            new_variable = int_var < att_value
    elif inequality == '==':
        new_variable = int_var == att_value
    print(new_variable)
    return new_variable

def processTimeParameters(time_val):
    time_val = time_val.lower()
    absolute_time = None
    if 'am' in time_val or 'pm' in time_val:
        if 'am' in time_val:
            raw_time_str = time_val.replace('am', '').replace(':', '.').strip()
            absolute_time = float(raw_time_str)
        if 'pm' in time_val:
            raw_time_str = time_val.replace('pm', '').replace(':', '.').strip()
            absolute_time = float(raw_time_str)
            if  1.0 < absolute_time < 12.00:
                absolute_time = absolute_time + 12
    elif ':'  in time_val:
        raw_time_str = time_val.replace(':', '.').strip()
        absolute_time = float(raw_time_str)
    elif 'sunrise + 1 hour' in time_val:
        absolute_time = float(7.30)
    elif 'sunrise' in time_val:
        absolute_time = float(6.30)
    elif 'sunset + 1 hour' in time_val:
        absolute_time = float(19.30)
    elif 'sunset' in time_val:
        absolute_time = float(18.30)
    else:
        raw_time_str = time_val.replace(':', '.').strip()
        absolute_time = float(raw_time_str)
    return absolute_time

def getDomainKnowledgeOnCapability(cap_name):
    # get capability summary
    record = prod_cap_summary_file_read.loc[prod_cap_summary_file_read['cap_ID'] == cap_name]
    series_summary = record['Summary']
    series_index = series_summary.index[0]
    cap_summary = series_summary[series_index]
    return cap_summary

def getPossibleAttrValues(cap_name, attr):
    attr_values = []
    for cap in prod_cap_sum_list:
        if cap == cap_name:
            summary = getDomainKnowledgeOnCapability(cap)
            pattern_find_attrs = r'attributes:(.*?), commands'
            matching_attrs = re.search(pattern_find_attrs, summary)
            pattern_seperate_attrs =  r"'(.*?)'"
            attributes = re.findall(pattern_seperate_attrs, matching_attrs.group(1))
            for attribute in attributes:
                if attr in attribute:
                    if '=' in attribute:
                        attr_info = attribute.split('=')
                        attr_values = attr_info.pop().replace('[','').replace(']','').split(',')
                        attr_name = attr_info.pop()
                        if attr in attr_name:
                            print('found attribute !')
                            print(attr_values)
                            return attr_values
                    else:
                        print('no predefined values for attr..')

    return attr_values

def getPossibleCommands(cap_name):
    all_commands = []
    for cap in prod_cap_sum_list:
        if cap == cap_name:
            summary = getDomainKnowledgeOnCapability(cap)
            pattern_seperate_commands=  r'"(.*?)"'
            all_commands_str = re.findall(pattern_seperate_commands, summary.split('commands:').pop())
            for cmd in all_commands_str:
                cmd = cmd.split('(')
                cmd_name = cmd[0]
                all_commands.append(cmd_name)

    return all_commands

def extractAttrValueAndInequality(cond, is_period, period_attr):
    cap_att_split = None
    inequality = None
    # if a range is given with inequality then is_period true
    if '>=' in cond:
        cap_att_split = cond.split(">=")
        inequality = '>='
    elif '<=' in cond:
        cap_att_split = cond.split("<=")
        inequality = '<='
    elif '>' in cond:
        cap_att_split = cond.split(">")
        inequality = '>'
    elif '<' in cond:
        cap_att_split = cond.split("<")
        inequality = '<'
    elif '==' in cond:
        cap_att_split = cond.split("==")
        if not is_period:
            # UPDATED: to reflect the action is valid from the time or defined value onward
            # e.g. if now.time == 9 am, the action is effective from 9 am to until another constraint
            inequality = '>='
        else:
            inequality = '=='
    if is_period:
        att_value = cond.replace(inequality, '').strip()
        cap_attribute = period_attr
    else:
        att_value = cap_att_split.pop()
        cap_attribute = cap_att_split.pop()
    return cap_attribute, att_value, inequality

def processTriggercondition(tr_cond):
    is_attr_binary_or_multi = False
    inequality = None
    cap_attribute = None
    att_value = None
    cap_name = None
    full_cap_name = None
    att_value2 = None
    inequality2 = None
    is_period = False
    cap_name_attr = None

    term_array = tr_cond.split(".")
    cond = term_array.pop()
    # analyse inequality periods
    if '>' in tr_cond and '<' in tr_cond or tr_cond.count('<') == 2 or tr_cond.count('<') == 2:
        is_period = True
        pattern_between = r'[<>]=?\s*(.*?)\s*[<>]=?'
        cap_name_attr_list = re.findall(pattern_between, tr_cond)
        cap_name_attr = cap_name_attr_list.pop()
        operands = tr_cond.split(cap_name_attr)
        left_operand = operands[0]
        right_operand = operands[1]
        cap_attribute, att_value, inequality = extractAttrValueAndInequality(left_operand, is_period, cap_name_attr)
        cap_attribute, att_value2, inequality2 = extractAttrValueAndInequality(right_operand, is_period, cap_name_attr)
    else:
        # check if the constraint is using inequalities
        if '>' in cond or '<' in cond or 'time' in cond:
            cap_attribute, att_value, inequality  = extractAttrValueAndInequality(cond, is_period, None)
        else:
            cap_attribute = cond.split("==")[0]
            att_value = cond.split("==")[1]
    if is_period:
        full_cap_name = cap_name_attr
    else:
        full_cap_name = "_".join(term_array)
    cap_name = term_array.pop()

    if 'time' in cap_attribute and not is_period:
        att_value = processTimeParameters(att_value)
    if 'time' in cap_attribute and is_period:
        att_value2 = processTimeParameters(att_value2)

    attribute_values_in_capability = getPossibleAttrValues(cap_name, cap_attribute)
    if len(attribute_values_in_capability)>0:
        is_attr_binary_or_multi = True
        # if not create a constant Int or StringVal
    else:
        #consider binary for now
        is_attr_binary_or_multi = True

    return full_cap_name, cap_name, cap_attribute, att_value,inequality,is_period, att_value2, inequality2, attribute_values_in_capability, is_attr_binary_or_multi

def processActions(ac_conseq):
    is_no_of_commands_binary_or_multi = False
    term_array = ac_conseq.split(".")
    command = term_array.pop()
    command_name = command.split('(')[0]
    full_cap_name = "_".join(term_array)
    cap_name = term_array.pop()
    all_commands_in_capability = getPossibleCommands(cap_name)
    if len(all_commands_in_capability)>0:
        is_no_of_commands_binary_or_multi = True
        #if not create a constant Int or StringVal and set == True

    return full_cap_name, cap_name, command_name, all_commands_in_capability, is_no_of_commands_binary_or_multi

def updateRuleSet(before_z3_rules, all_rule_variables):
    ##################################################### START #####################################################
    #UPDATE: Add additional conditions or clauses to rules  when numberic values such as time, temperature, is included
    # Reason: The general nature of time is to increase all the time, and temperature, humidity can be either way.
    # Therefore, unless specifically defined as less than, it is considered as greater than or equal.
    # Following section try to find the constraint that negate (or add upper-bound) the action in rules with time/temp/hum  in trigger
    #################################################################################################################
    print('*************** START ************************')
    print(before_z3_rules)
    print(len(before_z3_rules))
    # check which rules has inequality
    rules_with_inequality = []
    found_ineq_var = []
    for v2 in all_rule_variables:
        if v2['inequality']:  # e.g. now.time
            z3var_with_ineq = v2['extra-variable']
            if z3var_with_ineq not in found_ineq_var:
                found_ineq_var.append(z3var_with_ineq)
                print(z3var_with_ineq)
                for b_rule in before_z3_rules:
                    for z3var_with_ineq in b_rule['and_triggers'] or z3var_with_ineq in b_rule['or_triggers']:
                        rules_with_inequality.append(b_rule)
    print(len(rules_with_inequality))
    a_command_found = False
    for v in all_rule_variables:
        z3var = None # currently checking
        rule_with_positive_action = []
        rule_with_negation = []

        if v['inequality'] is None: # e.g. switch_on
            z3var = v['variable'] # get command name
            print(z3var)
            a_command_found =  True
            # check which rule's action has it or it's negation
            for b_rule in before_z3_rules:
                for a in b_rule['actions']:
                    if a == z3var:
                        rule_with_positive_action.append(b_rule)
                    if a == Not(z3var):
                        # means there is a rule to automatically stop the
                        rule_with_negation.append(b_rule)
            # check if inequality variables are in any of the above rules
            # create new z3 variable to mark the negation action completion
            command_completed = Bool('command_completed')
            for ineq_rule in rules_with_inequality:
                for pve_rule in rule_with_positive_action:
                    if ineq_rule == pve_rule:
                        print('found pve_rule')
                        print(ineq_rule)
                        # SHOULD?? add to the lower margin
                        #add new trigger condition to the pve_rule, only affect the and_triggers
                        has_new_trigger = False
                        for x in pve_rule['and_triggers']:
                            if Not(command_completed) == x:
                                has_new_trigger = True
                        if not has_new_trigger:
                            current_triggers = pve_rule['and_triggers']
                            before_z3_rules.remove(pve_rule)
                            current_triggers.append(Not(command_completed))
                            pve_rule['and_triggers'] = current_triggers
                            before_z3_rules.append(pve_rule)
                for ng_rule in rule_with_negation:
                    if ineq_rule == ng_rule:
                        print('found ng_rule')
                        has_new_action = False
                        for x in ng_rule['actions']:
                            if command_completed == x:
                                has_new_action = True
                        # add a new action for the negation rule with same name as above trigger
                        if not has_new_action:
                            current_actions = ng_rule['actions']
                            before_z3_rules.remove(ng_rule)
                            current_actions.append(command_completed)
                            ng_rule['actions'] = current_actions
                            before_z3_rules.append(ng_rule)
    return before_z3_rules

def createZ3variablesAndCastValuesForInEqualities(full_cap_name, cap_attribute,att_value, is_period):
    int_or_float_var = None
    if is_period:
        if 'time' in cap_attribute:
            int_or_float_var = Real(cap_attribute.strip())
    elif 'time' in cap_attribute:
        int_or_float_var = Real(full_cap_name.strip() + '_' + cap_attribute.strip())
    else:
        int_or_float_var = Int(full_cap_name.strip() + '_' + cap_attribute.strip())
    if type(att_value) == str:
        try:
            att_value = int(att_value)
        except ValueError:
            att_value = 50
            print('error casting')
    elif type(att_value) == float:
        att_value = float(att_value)
    return int_or_float_var, att_value

def createZ3TriggerConstraints(tr_cond, trigge_conditions, all_rule_variables):
    print('......createZ3TriggerConstraints..........')
    full_cap_name, cap_name, cap_attribute, att_value, inequality,is_period,att_value2, inequality2, attribute_values_in_capability, is_attr_binary_or_multi = processTriggercondition(
        tr_cond)
    is_relavant_variable_created = False
    new_variable = None
    for rule_var in all_rule_variables:
        if rule_var['full_cap_name'] == full_cap_name and rule_var['attr'] == cap_attribute:
            if inequality is not None and rule_var['inequality'] == inequality and rule_var['att_value'] == att_value:
                is_relavant_variable_created = True
                trigge_conditions.append(rule_var['variable'])
            elif inequality is None:
                is_relavant_variable_created = True
                if rule_var['att_value'] != att_value:
                    print('use negation')  # do not create a new variable
                    print(Not(rule_var['variable']))
                    trigge_conditions.append(Not(rule_var['variable']))
                if rule_var['att_value'] == att_value:
                    trigge_conditions.append(rule_var['variable'])
    if not is_relavant_variable_created:
        if is_attr_binary_or_multi:
            variable_info = {}
            variable_info['capability'] = cap_name
            variable_info['attr'] = cap_attribute
            variable_info['att_value'] = att_value
            variable_info['values'] = attribute_values_in_capability
            variable_info['type'] = "trigger"
            variable_info['inequality'] = inequality
            variable_info['full_cap_name'] = full_cap_name
            variable_info['is_period'] = is_period
            variable_info['att_value2'] = att_value2
            variable_info['inequality2'] = inequality2
            if is_period:
                int_or_float_var, att_value = createZ3variablesAndCastValuesForInEqualities(full_cap_name, cap_attribute, att_value, True)
                variable_info['extra-variable'] = int_or_float_var
                int_or_float_var, att_value2 = createZ3variablesAndCastValuesForInEqualities(full_cap_name, cap_attribute, att_value2, True)
                new_variable1 = utilInequalty(variable_info['inequality'], variable_info['extra-variable'], att_value, True)
                new_variable2 = utilInequalty(variable_info['inequality2'], variable_info['extra-variable'], att_value2, False)
                variable_info['variable1_period'] = new_variable1
                variable_info['variable2_period'] = new_variable2
                trigge_conditions.append(new_variable1)
                trigge_conditions.append(new_variable2)
            elif inequality is not None:
                int_or_float_var, att_value = createZ3variablesAndCastValuesForInEqualities(full_cap_name, cap_attribute, att_value, False)
                variable_info['extra-variable'] = int_or_float_var
                new_variable = utilInequalty(variable_info['inequality'], variable_info['extra-variable'], att_value, False)
                variable_info['variable'] = new_variable
                trigge_conditions.append(new_variable)
            else:
                new_variable = Bool(full_cap_name.strip()+'_'+cap_attribute.strip() + '_' + att_value.strip())
                variable_info['variable'] = new_variable
                trigge_conditions.append(new_variable)

            all_rule_variables.append(variable_info)
            # add as the true case
            print(trigge_conditions)

    return trigge_conditions, all_rule_variables

def createZ3ActionConsequences(ac_conseq, rule_conclusions, all_rule_variables, is_trigger_for_wait):
    print('......createZ3ActionConsequences..........')
    is_relavant_variable_created = False
    is_no_of_commands_binary_or_multi = False
    full_cap_name = None
    command_name = None
    cap_name = None
    inequality = None
    all_commands_in_capability = None
    time_period_in_seconds = None
    print(ac_conseq)
    if 'wait' in ac_conseq or 'WAIT' in ac_conseq:
        command_name = 'wait'
        pattern_time_parameter = r'\(\"(.*?)\"\)'
        time_parameter = re.findall(pattern_time_parameter, ac_conseq)[0]
        pattern_time_period = r'\b\d+\b'
        time_period =re.findall(pattern_time_period,time_parameter)[0]
        time_unit = time_parameter.replace(time_period, '').strip()
        command_name = 'wait'
        if 'minute' in time_unit:
            time_period_in_seconds = int(time_period)*60
        else:
            time_period_in_seconds = int(time_period)
        full_cap_name = None
        cap_name = None
        is_no_of_commands_binary_or_multi = True

    else:
        full_cap_name, cap_name, command_name, all_commands_in_capability, is_no_of_commands_binary_or_multi = processActions(ac_conseq)

    for rule_var in all_rule_variables:
        if full_cap_name is not None and rule_var['full_cap_name'] == full_cap_name:
            is_relavant_variable_created = True
            if command_name in rule_var['variable'].decl().name():
                rule_conclusions.append(rule_var['variable']) #if same vairalbe is relevant use it
            else:
                print('use negation')  # do not create a new variable
                print(Not(rule_var['variable']))
                rule_conclusions.append(Not(rule_var['variable']))

    if not is_relavant_variable_created:
        if is_no_of_commands_binary_or_multi:
            variable_info = {}
            if 'wait' in ac_conseq or 'WAIT' in ac_conseq:
                int_command = Int(command_name.strip())
                if is_trigger_for_wait:
                    new_variable = int_command > time_period_in_seconds
                    inequality = '>'
                else:
                    new_variable = int_command == time_period_in_seconds
                    inequality = '=='
                variable_info['extra-variable'] = int_command

            else:
                new_variable = Bool(full_cap_name.strip() + '_' + command_name.strip())
            variable_info['variable'] = new_variable
            variable_info['capability'] = cap_name
            variable_info['command'] = command_name
            variable_info['all_commands'] = all_commands_in_capability
            variable_info['type'] = "action"
            variable_info['full_cap_name'] = full_cap_name
            variable_info['inequality'] = inequality
            all_rule_variables.append(variable_info)
            # add as the true case
            print(new_variable)
            rule_conclusions.append(new_variable)
    return rule_conclusions, all_rule_variables

def createZ3Rule(trigge_conditions, or_trigge_conditions, rule_conclusions, is_else):
    rule_conditions_final = None
    rule_conclustions_final = None
    rule_or_conditions = None

    if len(or_trigge_conditions)>=1:
        rule_or_conditions = Or(or_trigge_conditions)
    if len(trigge_conditions)>1:
        if is_else:
            rule_conditions_final = And(Not(trigge_conditions))
        else:
            rule_conditions_final = And(trigge_conditions)
    elif len(trigge_conditions)==1:
        if is_else:
            rule_conditions_final = Not(trigge_conditions[0])
        else:
            rule_conditions_final = trigge_conditions[0]
    if len(rule_conclusions) > 1:
        rule_conclustions_final = And(rule_conclusions)
    elif len(rule_conclusions) ==1:
        rule_conclustions_final = rule_conclusions[0]

    if len(or_trigge_conditions) >= 1 and len(trigge_conditions) >= 1:
        rule_conditions_final = And(rule_conditions_final,rule_or_conditions )
    elif len(or_trigge_conditions) >= 1:
        rule_conditions_final = rule_or_conditions
    rule = Implies(rule_conditions_final, rule_conclustions_final)
    return rule

def transformRuleParamsToZ3Variables(trigger_clause,action_clause, all_rule_variables, is_else):
    print('......transformRuleToZ3formula..........')
    rules = []

    ###### create Z3 trigger constraints
    or_trigge_conditions = []
    trigge_conditions = []
    for trigger in trigger_clause:
         # combine or conditions in trigger
        if len(trigger)>1:
            print('or conditions')
            for tr in trigger:
                # get the command name, which is the last element
                print(tr.split(".").pop())
                # check if the attribute is a boolean using prod capability schema info
                or_trigge_conditions, all_rule_variables = createZ3TriggerConstraints(tr, or_trigge_conditions,
                                                                                   all_rule_variables)
        elif len(trigger) == 1:
            tr_cond = trigger[0].strip()
            print(tr_cond)
            trigge_conditions, all_rule_variables = createZ3TriggerConstraints(tr_cond, trigge_conditions, all_rule_variables)

    ## If wait action is in the action_clause, remove actions after wait and add as actions of new rule
    new_trigger_conditions = [] #previous actions until wait
    new_action_conditions = []  # post actions after wait
    is_wait = False
    for action in action_clause:
        ac_conseq = None
        if len(action) == 1:
            ac_conseq = action[0].strip()
            print(ac_conseq)
        if not is_wait:
            new_trigger_conditions, all_rule_variables = createZ3ActionConsequences(ac_conseq, new_trigger_conditions, all_rule_variables, True)

        else:
            new_action_conditions, all_rule_variables = createZ3ActionConsequences(ac_conseq, new_action_conditions, all_rule_variables, False)
            # remove the post actions from action_clause
            action_clause.remove(action)
        if 'wait' in ac_conseq:
            is_wait = True

    ###### create Z3 actions (rule consequences)
    rule_conclusions = []
    print(trigge_conditions)
    print(action_clause)
    for action in action_clause:
        if len(action) == 1:
            ac_conseq = action[0].strip()
            print(ac_conseq)
            rule_conclusions, all_rule_variables = createZ3ActionConsequences(ac_conseq, rule_conclusions, all_rule_variables, False)

    # create new rule in Z3 semantics for WAIT rules
    if is_wait:
        new_rule = {'and_triggers': new_trigger_conditions, 'or_triggers': or_trigge_conditions,
                    'actions': new_action_conditions, 'is_else': is_else, 'is_wait': is_wait}
        rules.append(new_rule)

    # create the rule in Z3 semantics
    new_rule = {}
    new_rule['and_triggers'] = trigge_conditions
    new_rule['or_triggers'] = or_trigge_conditions
    new_rule['actions'] = rule_conclusions
    new_rule['is_else'] = is_else
    new_rule['is_wait'] = is_wait
    rules.append(new_rule)
    return rules, all_rule_variables

def getRulesSetInZ3(rule_set, all_rule_variables):
    print('......getRulesSetInZ3..........')
    z3_rules = []
    before_z3_rules = []
    has_else = False
    else_actions = None
    for rule in rule_set:
        print('.............rule processing.............')
        rule_split = rule.split(',')
        conditions = rule_split[0].replace('If', '').replace('IF', '').replace('"','')#.replace(' ','')
        actions = rule_split[1].replace('then', '').replace('THEN', '')
        if len(rule_split) == 3:
            has_else = True
            else_actions = rule_split[2].replace('else', '').replace('ELSE', '')
        # identify conjunctions and disjunctions in the conditions/triggers
        conjunc = conditions.split(' and ')
        trigger_clause = []
        action_clause = []
        else_action_clause = []

        for conj in conjunc:
            disjunc = conj.split(' or ')
            trigger_clause.append(disjunc)

        actionsC = actions.strip().split(' and ')
        for ac in actionsC:
            action_clause.append([ac])

        if has_else:
            else_actions_commands = else_actions.strip().split(' and ')
            for ac in else_actions_commands:
                else_action_clause.append([ac])
            else_rule, all_rule_variables = transformRuleParamsToZ3Variables(trigger_clause, else_action_clause, all_rule_variables, has_else)
            before_z3_rules = before_z3_rules + else_rule

        print(trigger_clause)
        print(action_clause)
        rules, all_rule_variables = transformRuleParamsToZ3Variables(trigger_clause, action_clause, all_rule_variables, False)
        before_z3_rules = before_z3_rules + rules

    #UPDATE the rule set if necesary
    # before_z3_rules = updateRuleSet(before_z3_rules, all_rule_variables)
    print(before_z3_rules)



    print('*************** END **************************')
    ###################################################### END  #####################################################


    # create z3 rules
    for b_rule in before_z3_rules:
        z3_rule = createZ3Rule(b_rule['and_triggers'], b_rule['or_triggers'], b_rule['actions'], b_rule['is_else'])
        z3_rules.append(z3_rule)

    return z3_rules, all_rule_variables

def prepreocessRuleString(gpt_rule_set_string):
    if 'Rules for Actual Task:' in gpt_rule_set_string:
        gpt_rule_set = gpt_rule_set_string.replace('Rules for Actual Task:','')
    # process input rule set to separate each generated rule
    pattern = r'\[(.*?)\]'
    gpt_rule_set = re.findall(pattern, gpt_rule_set_string)
    return gpt_rule_set

def z3solverCheckandSaveResults(solver,all_rule_variables, df, gpt_rule_set, z3_rule_set, constraints):
    # Check satisfiability
    print("###################### start check #######################")
    if solver.check() == sat:
        model = solver.model()

        print("Satisfiable.")
        print("Model:")
        for vars in all_rule_variables:
            if vars['type'] == 'trigger' and vars['inequality'] is not None:
                print(str(vars['extra-variable']) + ": ", model[vars['extra-variable']])
            elif vars['type'] == 'action' and vars['inequality'] is not None:
                print(str(vars['extra-variable']) + ": ", model[vars['extra-variable']])
            else:
                print(str(vars['variable']) + ": ", model[vars['variable']])

        # update output file...
        df = pd.DataFrame([[i, gpt_rule_set, z3_rule_set, solver.check(), model,constraints]])  # columns=["cap_ID", "Summary"]
        with pd.ExcelWriter(z3_output_file, mode='a', engine='openpyxl', if_sheet_exists="overlay") as writer:
            df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False,
                        header=False)

    else:
        print("Unsatisfiable.")
        # update output file...
        df = pd.DataFrame([[i, gpt_rule_set, z3_rule_set, solver.check(),'', constraints]])  # columns=["cap_ID", "Summary"]
        with pd.ExcelWriter(z3_output_file, mode='a', engine='openpyxl', if_sheet_exists="overlay") as writer:
            df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False,
                        header=False)
    print("###################### end check #########################")
    return

def checkZ3Satisfiability(i, gpt_rule_set, z3_rule_set, all_rule_variables):
    print('.................checkZ3Satisfiability.................')
    # additional constraints
    print('initial constraints..')
    added_attr_list = []
    saved_int_vars = []
    saved_constraintes = []

    for vars in all_rule_variables:
        if vars['type'] == 'trigger'and vars['inequality'] is None and vars['attr'] not in added_attr_list:
            # solver.add(vars['variable'])
            saved_constraintes.append(vars['variable'])
            added_attr_list.append(vars['attr'])
    for vars in all_rule_variables:
        if vars['type'] == 'trigger' and vars['inequality'] is not None and vars['attr'] not in added_attr_list:
            added_attr_list.append(vars['attr'])
            if vars not in saved_int_vars:
                saved_int_vars.append(vars)

    relation_array = ["<",">","=="]
    # save the current state of solver
    # current_solver = solver.translate(solver.ctx)
    if len(saved_int_vars) > 0:
        for v in saved_int_vars:
            att_value = None
            if type(v['att_value']) == str:
                try:
                    att_value = int(v['att_value'])
                except ValueError:
                    att_value = 50  # Int(vars['att_value'])
                    print('error casting')
            elif type(v['att_value'] == float):
                att_value = v['att_value']
            for relation in relation_array:
                print('.............. add constraint............')
                saved_constraintes.append(utilInequalty(relation, v['extra-variable'], att_value, False))
                #create z3 solver
                solver = Solver()
                solver.add(And(z3_rule_set))
                for constraint in saved_constraintes:
                    solver.add(constraint)
                z3solverCheckandSaveResults(solver, all_rule_variables, df, gpt_rule_set, z3_rule_set, saved_constraintes)
                saved_constraintes.pop()

    else:
        solver = Solver()
        solver.add(And(z3_rule_set))
        for constraint in saved_constraintes:
            solver.add(constraint)
        z3solverCheckandSaveResults(solver, all_rule_variables, df, gpt_rule_set, z3_rule_set, saved_constraintes)

################################ start the program #############################################
# get rule set
i= 0
for gpt_rule_set_string in gpt_generated_rules_list:
    i = i + 1
    print('............................begins..('+str(i)+')..............................')
    all_rule_variables = []
    gpt_rule_set = prepreocessRuleString(gpt_rule_set_string)
    print(gpt_rule_set)
    # transform the rule set into Z3 formulas
    z3_rule_set, all_rule_variables = getRulesSetInZ3(gpt_rule_set, all_rule_variables)
    print(z3_rule_set)
    # check satisfiable of the gpt generated rules set
    checkZ3Satisfiability(i, gpt_rule_set, z3_rule_set, all_rule_variables)

################################ end the program #############################################