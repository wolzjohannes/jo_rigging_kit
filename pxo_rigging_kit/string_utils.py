import re


def camel_to_snake(camel_case_str):
    """
    Given a string replace camel case with underscore.
    For example:
        "myCustomName" -> "my_custom_name"
    """
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', camel_case_str)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def snake_to_camel(snake_str):
    """
    Given a string replace underscores with camel case.
    For example:
        "my_custom_name" -> "myCustomName"
    """
    return ''.join(word.capitalize() for word in snake_str.split('_'))


def increment_last_number(text):
    """
    Given a string, find the last number and increment it by one.
    For example:
        "myCustomName1" -> "myCustomName2"
    """
    # Find the last number in the string using regex
    match = re.search(r'\d+(?=\D*$)', text)
    if match:
        # Extract the number, increment it, and preserve the original length (e.g., for leading zeros)
        num = match.group()
        incremented = str(int(num) + 1).zfill(len(num))
        # Replace the last number with the incremented value
        return text[:match.start()] + incremented + text[match.end():]
    else:
        # If no number is found, append "_1" to the string
        return text + "_1"


def extract_integer(text):
    """
    Extracts the first sequence of digits from the input string and returns it as an integer.
    For example:
        "custom5_name" -> 5
        "item42test" -> 42

    Returns -1 if no digits are found
    """
    match = re.search(r'\d+', text)
    if match:
        try:
            return int(match.group())
        except ValueError:
            pass
    return -1
