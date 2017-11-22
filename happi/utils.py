"""
Basic module utilities
"""
############
# Standard #
############

###############
# Third Party #
###############


##########
# Module #
##########


def create_alias(name):
    """
    Clean an alias to be an acceptable Python variable
    """
    return name.replace(' ', '_').replace('.', '_').lower()
