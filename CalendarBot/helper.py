from datetime import datetime

def discord_time(date_time, set_format=None):
    """
    Convert date_time to a unix timestamp
    :param date_time:datetime to convert
    :param set_format: format used
    :return: Unix time stamp
    """
    if set_format is None:
        return f"<t:{int(datetime.timestamp(date_time))}>"
    else:
        return f"<t:{int(datetime.timestamp(date_time))}:{set_format}>"