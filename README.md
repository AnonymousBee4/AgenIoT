# AgenIoT

AgenIoT is a novel Large Language Model (LLM) based tool that automatically creates syntactically and semantically correct IoT automation rules based on a natural language description of the automation scenario. Our approach
performs few-shot and zero-shot learning with prompt engineering on LLM to eliminate the human effort in creating correct rules. We evaluate accuracy of our approach on a dataset of 123 smartapps of SmartThings, demonstrating that our approach creates syntactically correct rules for 84.14% of smartapp descriptions.

Phase_0: includes python scripts to prepare the input datasets  
Phase_1: includes two python scripts for capability selection and rule semantics generation (few-shot learning)  
Phase_2: includes a python script to check rule semantics satisfiablity using z3 solver  
Phase_3: incldues a python script for rule syntax generation (zero-shot learning)  

#Used python packages:  
python 3.9  
openai 1.31  
chromedriver_py 121.0  
openpyxl 3.1.2  
panda 2.1.3  
selenium 4.15.2  
z3-solver 4.13  
