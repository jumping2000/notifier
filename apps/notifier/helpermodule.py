'''Miscellaneous support functions for notifier'''
import re

def check_location(data, location)->bool:
    return (str(data).lower() =="" or str(data).lower()==location)

def check_notify(data)->bool:
    return False if (str(data).lower() in ["false","off","no"] or data == "0" or data == 0) else True

def convert(lst):  
    return {lst[1]: lst[3]}

# check if is true
def check_boolean(value)->bool:
    return str(value).lower() in ["true", "on", "yes", "1"]

def get_arg(args, key):
    key = args[key]
    if type(key) is str and key.startswith("secret_"):
        if key in secret_dict:
            return secret_dict[key]
        else:
            raise KeyError("Could not find {} in secret_dict".format(key))
    else:
        return key

def get_arg_list(args, key):
    arg_list = []
    if isinstance(args[key], list):
        arg = args[key]
    else:
        arg = (args[key]).split(",")
    for key in arg:
        if type(key) is str and key.startswith("secret_"):
            if key in secrets.secret_dict:
                arg_list.append(secrets.secret_dict[key])
            else:
                raise KeyError("Could not find {} in secret_dict".format(key))
        else:
            arg_list.append(key)
    return arg_list

def lg(message):
    self.log(message, level="DEBUG", ascii_encode=False)

# """Remove a key from a dict."""
def remove_key(d, key)->dict:
    r = dict(d)
    del r[key]
    return r

# """check if is an array and returns a list is input is a text"""
def return_array(target)->list:
    if isinstance(target, list):
        return target
    else:
        return list(target.split(","))
        
# def replace_regular(text, substitutions: list)->str:
#     if isinstance(text, str):
#         for old,new in substitutions:
#             text = re.sub(old, new, text.strip())
#         return text
#     else:
#          return text

def replace_regular(text: str, substitutions: list) -> str:
        for old, new in substitutions:
            regex = re.compile(old)
            text = re.sub(regex, new, str(text).strip())
        return text

def replace_language(s: str)->str:
    return (s[:2])

# """Remove all tags from a string."""
def remove_tags(text: str)->str:
    regex = re.compile("<.*?>")
    return re.sub(regex, "", str(text).strip())

def has_numbers(string):
    numbers = re.compile("\d{4,}|\d{3,}\.\d")
    return numbers.search(string)
