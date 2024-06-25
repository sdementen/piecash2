import re

import inflect

inflect.def_classical["names"] = False
engine = inflect.engine()


def camelize(string, uppercase_first_letter=True):
    """
    Convert strings to CamelCase.
    """
    if uppercase_first_letter:
        return re.sub(r"(?:^|_)(.)", lambda m: m.group(1).upper(), string)
    else:
        return string[0].lower() + camelize(string)[1:]


def underscore(word):
    """
    Make an underscored, lowercase form from the expression in the string.
    """
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", word)
    word = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", word)
    word = word.replace("-", "_")
    return word.lower()


def pluralize(word):
    return engine.plural_noun(word)
