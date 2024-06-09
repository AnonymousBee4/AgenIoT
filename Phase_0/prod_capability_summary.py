import json
import pandas as pd

# input
prod_capability_file = '../input/prod_capabilities.xlsx'
prod_capability_file_read = pd.read_excel(prod_capability_file, sheet_name=0)
prod_cap_schemas_list = prod_capability_file_read.Json_Content.tolist()

# output
prod_cap_summary_output_file =  '../output/prod_cap_summaries.xlsx'
df = pd.DataFrame(columns=["cap_ID", "Summary"])
df.to_excel(prod_cap_summary_output_file, index=False)

for prod_cap_schema in prod_cap_schemas_list:
    prod_cap_schema = json.loads(prod_cap_schema)
    id = prod_cap_schema['id']
    if id == 'switch':
        print('switch')
    attributes = prod_cap_schema['attributes']
    commands = prod_cap_schema['commands']

    # Get information on attributes: name, type, accepted values (optional)
    attr_list = []
    if len(attributes) > 0:
        for attr, value in attributes.items():
            property_values = value['schema']['properties']['value']
            data_type = property_values['type']
            values = None
            try:
                values = [property_values['enum']]
            except KeyError:
                print('no enums')

            attr_data = None
            if values is None:
                attr_data = attr + '(' + data_type +')'
            else:
                attr_data = attr + '(' + data_type +')=[' + ','.join(values[0]) +']'
            attr_list.append(attr_data)

    # Get information on commands: name, if any arguments? name, type (optional)
    all_commands = []
    if len(commands) > 0:
        for command, c_value in commands.items():
            args = c_value['arguments']
            args_data = []
            if type(args) is list and len(args) > 0:
                for arg in args:
                    arg_name = arg['name']
                    arg_type = arg['schema']['type']
                    # check for enums for attribute
                    arg_enums = None
                    try:
                        arg_enums = arg['schema']['enum']
                    except KeyError:
                        print('no enums')

                    if arg_enums is not None:
                        enum_str = '['+','.join(arg_enums)+']'
                        args_data.append(arg_name + '(' + arg_type + ')'+ '='+enum_str)
                    else:
                        args_data.append(arg_name+ '('+ arg_type + ')')

            if len(args_data) > 0:
                cmd = command+ '(arguments = ' + str(args_data)+ ')'
            else:
                cmd = command + '(arguments = \'[]\')'
            all_commands.append(cmd)
    else:
        print('no commands')

    actions = 'commands: ' + str(all_commands)
    trigger_attributes = 'attributes: '+str(attr_list)
    capability_info = id +'=[' +trigger_attributes +', '+ actions + ']'
    print(capability_info)
    df = pd.DataFrame([[id, capability_info]])
    with pd.ExcelWriter(prod_cap_summary_output_file, mode='a', engine='openpyxl', if_sheet_exists="overlay") as writer:
        df.to_excel(writer, sheet_name="Sheet1", startrow=writer.sheets["Sheet1"].max_row, index=False, header=False)